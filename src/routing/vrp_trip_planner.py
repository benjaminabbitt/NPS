#!/usr/bin/env python3
"""
VRP-Based Trip Planner: Partition ALL NPS sites using multi-vehicle routing

Strategy:
- Use OR-Tools VRP (Vehicle Routing Problem) with multiple vehicles
- Each vehicle = one trip from home base
- Flexible trip lengths: 3-4 days, 1 week, 2 weeks
- Configurable home base location
- 4 hours per site (stamps + exploration), 10 hours per day (realistic pacing), 55 mph average speed
- Targets ~2 sites per day for sustainable travel
- Penalty for using extra vehicles (encourages fewer, fuller trips)
- Includes OpenStreetMap and Google Maps route links

CRITICAL CONSTRAINT - Operating Hours:
- Sites MUST be visited within operating hours unless flagged with always_stamp_available
- Arrival must be during operating hours, but visit can extend past closing
- Trips with violations at non-flagged sites are INVALID and require manual adjustment
- Use parameter optimization (optimize_trip_parameters.py) to find valid configurations

KNOWN LIMITATION - Day Boundaries:
- Current implementation uses continuous time dimension without explicit day breaks
- Days are calculated post-hoc by dividing cumulative time by hours_per_day
- Does NOT optimize for end-of-day positioning travel toward next day's sites
- Future enhancement: Model days as discrete units with positioning travel at end of day
"""
import json
import yaml
import math
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from timezonefinder import TimezoneFinder
from nps_data_loader import NPSDataLoader, NPSSite

# Initialize timezone finder (global, reused across all lookups)
TZ_FINDER = TimezoneFinder()


def create_osm_route_link(waypoints: List[tuple]) -> str:
    """Create OpenStreetMap Directions link with multiple waypoints"""
    route_points = ";".join([f"{lat},{lon}" for lat, lon in waypoints])
    return f"https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route={route_points}"


def create_google_maps_link(waypoints: List[tuple]) -> str:
    """Create Google Maps directions link"""
    if not waypoints:
        return ""
    start = waypoints[0]
    end = waypoints[-1]
    url = f"https://www.google.com/maps/dir/{start[0]},{start[1]}"
    for lat, lon in waypoints[1:-1]:
        url += f"/{lat},{lon}"
    url += f"/{end[0]},{end[1]}"
    return url


def create_geojson_route(trip_data: Dict) -> Dict:
    """Create GeoJSON representation of the trip route"""
    coordinates = []
    properties = []

    for stop in trip_data['route_details']:
        coordinates.append([stop['lon'], stop['lat']])  # GeoJSON uses [lon, lat]
        properties.append({
            'name': stop['site'],
            'arrival_day': stop['day'],
            'arrival_time': stop['time_of_day']
        })

    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates
                },
                "properties": {
                    "trip_number": trip_data['trip_number'],
                    "total_sites": trip_data['stats']['total_sites'],
                    "total_distance_miles": trip_data['stats']['total_distance_miles'],
                    "total_days": trip_data['stats']['total_days']
                }
            },
            *[
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [stop['lon'], stop['lat']]
                    },
                    "properties": prop
                }
                for stop, prop in zip(trip_data['route_details'], properties)
            ]
        ]
    }
    return geojson


# Default: Kirkwood, MO
DEFAULT_HOME_LAT = 38.5831
DEFAULT_HOME_LON = -90.4068
DEFAULT_HOME_NAME = "Kirkwood, MO"


@dataclass
class Site:
    """NPS Site"""
    name: str
    lat: float
    lon: float
    address: str = ""
    city: str = ""
    state: str = ""
    operating_hours: object = None  # OperatingHours from nps_data_loader
    always_stamp_available: bool = False  # True if stamps accessible 24/7

    @property
    def full_name(self) -> str:
        """Full name with city and state"""
        if self.city and self.state:
            return f"{self.name}, {self.city}, {self.state}"
        return self.name

    def get_timezone(self) -> str:
        """Get IANA timezone identifier for this site's location"""
        tz_name = TZ_FINDER.timezone_at(lat=self.lat, lng=self.lon)
        return tz_name or "America/Chicago"  # Default to Central if lookup fails


class VRPTripPlanner:
    """
    Multi-vehicle VRP for trip planning
    """

    def __init__(
        self,
        sites: List[Site],
        home_base: Tuple[str, float, float],  # (name, lat, lon)
        visit_hours_per_site: float = 2.0,
        hours_per_day: int = 15,  # Maximum: 06:00-21:00 operating window
        preferred_hours_per_day: int = 12,  # Preferred limit (soft, with penalties)
        target_trip_days: int = 3,
        max_trip_days: int = 4,
        avg_speed_mph: float = 55.0,
        prioritize_range: bool = True,  # Favor distant sites to maximize trips from home base
        verbose: bool = False
    ):
        # Add home base as depot (index 0)
        home_name, home_lat, home_lon = home_base
        self.home_base = Site(
            name=home_name,
            lat=home_lat,
            lon=home_lon
        )

        self.sites = [self.home_base] + sites
        self.visit_minutes_per_site = int(visit_hours_per_site * 60)
        self.hours_per_day = hours_per_day  # Hard maximum
        self.preferred_hours_per_day = preferred_hours_per_day  # Soft limit
        self.target_trip_minutes = target_trip_days * hours_per_day * 60
        self.max_trip_minutes = max_trip_days * hours_per_day * 60
        self.avg_speed_mph = avg_speed_mph
        self.prioritize_range = prioritize_range
        self.verbose = verbose

        # Trip start time preferences
        self.earliest_start_hour = 6  # Earliest tolerable start (6am)
        self.preferred_start_hour = 9  # Preferred start time (9am)
        self.earliest_start_minutes = self.earliest_start_hour * 60  # 360 min
        self.preferred_start_minutes = self.preferred_start_hour * 60  # 540 min

        # Calculate number of trips needed to cover all sites
        # Each trip should be approximately target_trip_days long
        # Estimate sites per trip based on available time:
        # - target_trip_days * hours_per_day * preferred_utilization / visit_hours_per_site
        # - Use 70% utilization to account for travel time (lower for short trips)
        if target_trip_days <= 2:
            preferred_utilization = 0.5  # More conservative for short trips
            min_sites = 3  # Allow fewer sites for short trips
        else:
            preferred_utilization = 0.7  # Standard for longer trips
            min_sites = 6

        estimated_sites_per_trip = int(target_trip_days * hours_per_day * preferred_utilization / visit_hours_per_site)
        sites_per_trip = max(min_sites, estimated_sites_per_trip)
        self.num_vehicles = max(1, min(30, (len(sites) + sites_per_trip - 1) // sites_per_trip))

        print(f"Configuring VRP:")
        print(f"  Sites: {len(sites)}")
        print(f"  Vehicles (trips): {self.num_vehicles}")
        print(f"  Target per trip: {target_trip_days} days ({self.target_trip_minutes//60}h)")
        print(f"  Max per trip: {max_trip_days} days ({self.max_trip_minutes//60}h)")

        if self.verbose:
            print(f"\nVerbose mode: Detailed site information")
            print(f"  Visit time per site: {visit_hours_per_site} hours ({self.visit_minutes_per_site} min)")
            print(f"  Hours per day: {hours_per_day} (hard max), {preferred_hours_per_day} (preferred)")
            print(f"  Average speed: {avg_speed_mph} mph")
            print(f"  Sites loaded (first 10):")
            for i, site in enumerate(sites[:10], 1):
                dist_from_home = self._haversine_distance(
                    home_lat, home_lon, site.lat, site.lon
                )
                print(f"    {i}. {site.name:40s} - {dist_from_home:6.1f} mi from home")

    def _haversine_distance(self, lat1, lon1, lat2, lon2):
        """Distance in miles"""
        R = 3959
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        return R * 2 * math.asin(math.sqrt(a))

    def _calculate_optimal_start_hour(self, route_details):
        """
        Calculate optimal trip start time based on first site operating hours.

        Strategy:
        - Calculate travel time from depot to first site
        - Set start time so we arrive exactly when first site opens
        - Prefer starting at preferred_start_hour (9am) if that works
        - Never start before earliest_start_hour (6am)

        Args:
            route_details: List of sites in order (first entry is depot)

        Returns:
            int: Optimal start hour (6-21)
        """
        if len(route_details) < 2:  # Only depot, no sites
            return self.preferred_start_hour

        depot = route_details[0]
        first_site = route_details[1]

        # Calculate actual travel time from depot to first site
        travel_distance_miles = self._haversine_distance(
            depot['lat'], depot['lon'],
            first_site['lat'], first_site['lon']
        )
        travel_time_minutes = (travel_distance_miles / self.avg_speed_mph) * 60

        # Check if first site has operating hours
        if 'operating_hours' in first_site and first_site.get('operating_hours'):
            op_hours = first_site['operating_hours']
            opens_field = op_hours.get('opens', 9 * 60)  # Default 9am

            # Handle both integer (minutes) and string (HH:MM) formats
            if isinstance(opens_field, str):
                # Parse "HH:MM" or "H:MM" format
                if ':' in opens_field:
                    parts = opens_field.split(':')
                    opens_minutes = int(parts[0]) * 60 + int(parts[1])
                else:
                    opens_minutes = 9 * 60  # Default if unparseable
            else:
                opens_minutes = opens_field

            # Calculate: what time do we need to start to arrive when site opens?
            # Required start = opening time - travel time
            required_start_minutes = opens_minutes - travel_time_minutes
            required_start_hour = required_start_minutes / 60.0

            # Prefer 9am, but adjust if needed to arrive at opening time
            if required_start_hour < self.earliest_start_hour:
                # Would need to start too early - clamp to earliest allowed (6am)
                # This means we'll arrive after opening time
                return self.earliest_start_hour
            elif required_start_hour <= self.preferred_start_hour:
                # Need to start before or at 9am to arrive at opening time
                # Round down to nearest hour for clean scheduling
                return int(required_start_hour)
            else:
                # Opening time is late enough that we can start at preferred time
                # and still arrive after/when it opens
                return self.preferred_start_hour

        # No operating hours - use preferred start time
        return self.preferred_start_hour

    def _create_distance_matrix(self):
        """Distance matrix in meters"""
        n = len(self.sites)
        matrix = [[0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j:
                    dist_miles = self._haversine_distance(
                        self.sites[i].lat, self.sites[i].lon,
                        self.sites[j].lat, self.sites[j].lon
                    )
                    matrix[i][j] = int(dist_miles * 1609.34)
        return matrix

    def _create_time_matrix(self, distance_matrix):
        """Time matrix in minutes (drive + visit)"""
        n = len(self.sites)
        matrix = [[0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j:
                    # Drive time
                    dist_miles = distance_matrix[i][j] / 1609.34
                    drive_minutes = int((dist_miles / self.avg_speed_mph) * 60)
                    # Add visit time (but not at depot)
                    visit_minutes = 0 if j == 0 else self.visit_minutes_per_site
                    matrix[i][j] = drive_minutes + visit_minutes
        return matrix

    def _check_site_fits_in_day(self, sites_in_day, new_site, start_location, day_budget_minutes, start_hour):
        """
        Check if adding new_site to sites_in_day fits within day budget and operating hours.

        Args:
            sites_in_day: List of site dicts already in the day
            new_site: Site dict to try adding
            start_location: (lat, lon) tuple of where the day starts
            day_budget_minutes: Total minutes available in the day
            start_hour: Hour when day starts (e.g., 6 or 9)

        Returns:
            (fits, arrival_time_minutes) - tuple of whether it fits and arrival time if it does
        """
        # Calculate cumulative time to reach new site
        current_time = 0
        current_location = start_location

        # Account for travel and visit time for all sites already in day
        for site in sites_in_day:
            travel_dist = self._haversine_distance(
                current_location[0], current_location[1],
                site['lat'], site['lon']
            )
            travel_time = (travel_dist / self.avg_speed_mph) * 60
            visit_time = self.visit_minutes_per_site
            current_time += travel_time + visit_time
            current_location = (site['lat'], site['lon'])

        # Now calculate time to reach new site
        travel_dist = self._haversine_distance(
            current_location[0], current_location[1],
            new_site['lat'], new_site['lon']
        )
        travel_time = (travel_dist / self.avg_speed_mph) * 60
        arrival_time = current_time + travel_time

        # Check if arrival + visit fits in day budget
        if arrival_time + self.visit_minutes_per_site > day_budget_minutes:
            return False, arrival_time

        # Check operating hours if site has them
        if 'operating_hours' in new_site and new_site['operating_hours']:
            op_hours = new_site['operating_hours']

            # Skip if stamps always available
            if new_site.get('always_stamp_available', False):
                return True, arrival_time

            # Calculate wall-clock arrival time
            arrival_minutes_of_day = (start_hour * 60) + arrival_time
            arrival_hour = (arrival_minutes_of_day // 60) % 24
            arrival_minute = arrival_minutes_of_day % 60

            # Parse operating hours
            opens_str = op_hours.get('opens', '09:00')
            closes_str = op_hours.get('closes', '17:00')

            if isinstance(opens_str, str) and ':' in opens_str:
                parts = opens_str.split(':')
                opens_minutes = int(parts[0]) * 60 + int(parts[1])
            else:
                opens_minutes = 9 * 60

            if isinstance(closes_str, str) and ':' in closes_str:
                parts = closes_str.split(':')
                closes_minutes = int(parts[0]) * 60 + int(parts[1])
            else:
                closes_minutes = 17 * 60

            # Check if arrival is within operating hours
            arrival_minutes_total = arrival_hour * 60 + arrival_minute
            if arrival_minutes_total < opens_minutes or arrival_minutes_total > closes_minutes:
                return False, arrival_time

        return True, arrival_time

    def _try_reorder_day(self, sites_in_day, new_site, start_location, day_budget_minutes, start_hour):
        """
        Try to reorder sites_in_day + new_site to make them all fit.

        Returns:
            (success, reordered_sites) - tuple of whether reordering worked and the new order
        """
        from itertools import permutations

        all_sites = sites_in_day + [new_site]

        # Try all permutations (limited to reasonable size)
        if len(all_sites) > 8:
            # Too many permutations, just return failure
            return False, sites_in_day

        # Try all orderings
        for perm in permutations(all_sites):
            # Check if this ordering fits
            all_fit = True
            for i in range(len(perm)):
                sites_so_far = list(perm[:i])
                site_to_check = perm[i]
                fits, _ = self._check_site_fits_in_day(
                    sites_so_far, site_to_check, start_location, day_budget_minutes, start_hour
                )
                if not fits:
                    all_fit = False
                    break

            if all_fit:
                # Found a valid ordering!
                return True, list(perm)

        # No valid ordering found
        return False, sites_in_day

    def _resequence_trip_with_violations(self, trip):
        """
        Resequence trip sites to fit operating hours constraints.

        Strategy:
        1. Take sites in VRP order
        2. Try to fit each into current day
        3. If doesn't fit, try reordering current day
        4. If reordering works, use it
        5. If not, move to next day

        Returns:
            (resequenced_trip, rejected_sites)
        """
        route_details = trip['route_details']
        rejected_sites = []

        # Extract non-depot sites
        sites_to_schedule = [stop for stop in route_details if stop.get('site_name') != self.home_base.name]

        if not sites_to_schedule:
            return trip, []

        # Constants
        DAILY_BUDGET_MINUTES = self.hours_per_day * 60
        PREFERRED_START_HOUR = self.preferred_start_hour  # 9am

        # Build days
        days = []  # List of lists of sites
        current_day_sites = []
        start_location = (self.home_base.lat, self.home_base.lon)

        print(f"\nResequencing Trip {trip['trip_number']}:")

        for i, site in enumerate(sites_to_schedule):
            # Try to fit site in current day
            fits, arrival_time = self._check_site_fits_in_day(
                current_day_sites, site, start_location, DAILY_BUDGET_MINUTES, PREFERRED_START_HOUR
            )

            if fits:
                # Site fits, add it
                current_day_sites.append(site)
                print(f"  ✓ Site {i+1}/{len(sites_to_schedule)}: {site.get('site_name')} fits in day {len(days)+1}")
            else:
                # Doesn't fit - try reordering
                print(f"  ✗ Site {i+1}/{len(sites_to_schedule)}: {site.get('site_name')} doesn't fit, trying reorder...")

                success, reordered = self._try_reorder_day(
                    current_day_sites, site, start_location, DAILY_BUDGET_MINUTES, PREFERRED_START_HOUR
                )

                if success:
                    # Reordering worked!
                    current_day_sites = reordered
                    print(f"    ✓ Reordering successful, site fits in day {len(days)+1}")
                else:
                    # Reordering failed - check if we can start a new day
                    if len(days) + 1 >= self.max_trip_minutes / DAILY_BUDGET_MINUTES:
                        # Trip is already at max days, reject this site
                        print(f"    ✗ Cannot fit in trip (max days reached), rejecting site")
                        rejected_sites.append({
                            'name': site.get('site_name', 'Unknown'),
                            'reason': 'Could not fit within trip day limits after reordering attempts',
                            'lat': site.get('lat'),
                            'lon': site.get('lon')
                        })
                        continue

                    # Start new day
                    days.append(current_day_sites)
                    # Update start location to last site of previous day
                    if current_day_sites:
                        last_site = current_day_sites[-1]
                        start_location = (last_site['lat'], last_site['lon'])

                    # Check if site fits in new day
                    fits_new_day, _ = self._check_site_fits_in_day(
                        [], site, start_location, DAILY_BUDGET_MINUTES, PREFERRED_START_HOUR
                    )

                    if fits_new_day:
                        current_day_sites = [site]
                        print(f"    ✓ Started day {len(days)+1} with this site")
                    else:
                        # Site doesn't even fit in a fresh day - reject it
                        print(f"    ✗ Site doesn't fit even in fresh day, rejecting")
                        rejected_sites.append({
                            'name': site.get('site_name', 'Unknown'),
                            'reason': 'Operating hours incompatible with trip schedule',
                            'lat': site.get('lat'),
                            'lon': site.get('lon'),
                            'operating_hours': site.get('operating_hours', {})
                        })
                        current_day_sites = []

        # Add last day if it has sites
        if current_day_sites:
            days.append(current_day_sites)

        # Now rebuild route_details with resequenced sites
        # (keeping depot at start and end)
        new_route_details = [route_details[0]]  # Depot
        for day_sites in days:
            new_route_details.extend(day_sites)
        new_route_details.append(route_details[0])  # Return to depot

        # Recalculate stats
        total_distance = 0
        total_time = 0
        for i in range(len(new_route_details) - 1):
            stop1 = new_route_details[i]
            stop2 = new_route_details[i + 1]
            dist = self._haversine_distance(
                stop1['lat'], stop1['lon'],
                stop2['lat'], stop2['lon']
            )
            total_distance += dist
            travel_time = (dist / self.avg_speed_mph) * 60
            visit_time = self.visit_minutes_per_site if stop2.get('site_name') != self.home_base.name else 0
            total_time += travel_time + visit_time

        resequenced_trip = {
            'trip_number': trip['trip_number'],
            'route_details': new_route_details,
            'stats': {
                'total_sites': len(new_route_details) - 2,  # Exclude depot at start and end
                'total_distance_miles': round(total_distance, 1),
                'total_time_hours': round(total_time / 60, 2),
                'total_days': len(days),
                'within_target': total_time <= self.target_trip_minutes,
                'within_max': total_time <= self.max_trip_minutes,
                'sites_rejected': len(rejected_sites),
                'resequenced': True
            }
        }

        return resequenced_trip, rejected_sites

    def solve(self):
        """Solve multi-vehicle VRP"""
        print(f"\nBuilding VRP model...")

        distance_matrix = self._create_distance_matrix()
        time_matrix = self._create_time_matrix(distance_matrix)

        if self.verbose:
            print(f"\nVerbose: Matrix dimensions: {len(distance_matrix)}x{len(distance_matrix)}")
            print(f"Verbose: Sample distances from depot (miles):")
            for i in range(1, min(6, len(self.sites))):
                dist_miles = distance_matrix[0][i] / 1609.34
                time_hrs = time_matrix[0][i] / 60
                print(f"  To {self.sites[i].name:40s}: {dist_miles:6.1f} mi, {time_hrs:5.2f} hrs (drive+visit)")

        # Create routing model
        manager = pywrapcp.RoutingIndexManager(
            len(self.sites),
            self.num_vehicles,
            0  # All vehicles start/end at depot (Kirkwood)
        )
        routing = pywrapcp.RoutingModel(manager)

        # Distance callback with optional range prioritization
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            base_distance = distance_matrix[from_node][to_node]

            if self.prioritize_range and from_node != 0 and to_node != 0:
                # When prioritizing range, reduce cost for traveling between distant sites
                # Calculate distance of both sites from home base (depot)
                from_home_dist = distance_matrix[0][from_node]
                to_home_dist = distance_matrix[0][to_node]

                # Average distance from home for this arc
                avg_dist_from_home = (from_home_dist + to_home_dist) / 2

                # Apply range bonus: reduce cost by up to 30% for very distant sites
                # Sites at 500 miles get ~30% reduction, sites at 250 miles get ~15%
                max_distance = 500 * 1609.34  # 500 miles in meters
                range_factor = min(avg_dist_from_home / max_distance, 1.0)
                range_discount = int(base_distance * range_factor * 0.3)

                return max(1, base_distance - range_discount)  # Ensure cost stays positive

            return base_distance

        distance_callback_index = routing.RegisterTransitCallback(distance_callback)

        # Time callback
        def time_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return time_matrix[from_node][to_node]

        time_callback_index = routing.RegisterTransitCallback(time_callback)

        # Set cost (minimize distance)
        routing.SetArcCostEvaluatorOfAllVehicles(distance_callback_index)

        # Add time dimension (per vehicle)
        # Increased slack to allow more flexibility with operating hours
        routing.AddDimension(
            time_callback_index,
            300,  # 5h slack for flexibility with operating hours
            self.max_trip_minutes,  # Hard limit: 4 days
            True,  # Start cumul to zero
            'Time'
        )

        time_dimension = routing.GetDimensionOrDie('Time')

        # Add operating hours constraints as soft time windows
        # For each site, we encourage arrivals during operating hours on ANY day
        # by setting multiple soft bounds for each possible day the trip could span
        OPERATING_HOURS_PENALTY = 500000  # High penalty for violating hours
        DAILY_MINUTES = self.hours_per_day * 60  # Minutes per day (e.g., 900 for 15 hours)

        if self.verbose:
            print(f"\nVerbose: Adding operating hours constraints")
            print(f"  Operating hours penalty: {OPERATING_HOURS_PENALTY}")
            print(f"  Daily budget: {DAILY_MINUTES} minutes")

        # For each site (except depot), add soft time window constraints
        max_possible_days = (self.max_trip_minutes // DAILY_MINUTES) + 1
        for i in range(1, len(self.sites)):  # Skip depot (index 0)
            site = self.sites[i]

            # Only add constraints if site has operating hours
            if not hasattr(site, 'operating_hours') or not site.operating_hours:
                continue

            # Skip if stamps are always available (24/7 access)
            if hasattr(site, 'always_stamp_available') and site.always_stamp_available:
                continue

            # Get operating hours in minutes from day start
            open_minutes = site.operating_hours.opens  # e.g., 540 for 9:00 AM
            close_minutes = site.operating_hours.closes  # e.g., 1020 for 5:00 PM

            # Estimate which day this site will likely be visited based on distance
            # This helps set appropriate time windows
            dist_from_home_miles = self._haversine_distance(
                self.home_base.lat, self.home_base.lon, site.lat, site.lon
            )
            travel_time_from_home_minutes = (dist_from_home_miles / self.avg_speed_mph) * 60
            visit_time = self.visit_minutes_per_site

            # Rough estimate: how much time to reach this site?
            # Assume average of 1 site per 3-4 hours (including travel + visit)
            estimated_time_to_reach = travel_time_from_home_minutes + visit_time
            estimated_day = max(0, min(int(estimated_time_to_reach / DAILY_MINUTES), max_possible_days - 1))

            if self.verbose and i <= 5:  # Show first 5 sites
                print(f"  Site {i}: {site.name}")
                print(f"    Operating hours: {open_minutes//60:02d}:{open_minutes%60:02d} - {close_minutes//60:02d}:{close_minutes%60:02d}")
                print(f"    Distance from home: {dist_from_home_miles:.1f} mi")
                print(f"    Estimated arrival day: {estimated_day + 1}")

            # For the estimated day, calculate the arrival window
            TRIP_START_HOUR = 6  # 6:00 AM trip start
            TRIP_START_OFFSET = TRIP_START_HOUR * 60  # Convert to minutes

            # Use estimated day for setting soft bounds, but show all possible days in verbose mode
            for day in range(max_possible_days):
                day_start_cumulative = day * DAILY_MINUTES
                window_open = day_start_cumulative + (open_minutes - TRIP_START_OFFSET)
                window_close = day_start_cumulative + (close_minutes - TRIP_START_OFFSET)
                window_open = max(0, window_open)

                if window_open < self.max_trip_minutes:
                    index = manager.NodeToIndex(i)

                    # Set soft bounds for the estimated day (most likely arrival day)
                    if day == estimated_day:
                        time_dimension.SetCumulVarSoftLowerBound(
                            index, window_open, OPERATING_HOURS_PENALTY
                        )
                        time_dimension.SetCumulVarSoftUpperBound(
                            index, window_close, OPERATING_HOURS_PENALTY
                        )

                        if self.verbose and i <= 5:
                            print(f"    Setting constraints for Day {day+1}: {window_open}-{window_close} min")

                    if self.verbose and i <= 5 and day <= 2:  # Show first few
                        marker = " (ACTIVE)" if day == estimated_day else ""
                        print(f"      Day {day+1}: cumulative window {window_open}-{window_close} min{marker}")

        # For each vehicle, add soft upper bound on trip length
        for vehicle_id in range(self.num_vehicles):
            end_index = routing.End(vehicle_id)
            time_dimension.SetCumulVarSoftUpperBound(
                end_index,
                self.target_trip_minutes,  # Target: 3 days
                100000  # Penalty for exceeding
            )

        # Small penalty for using vehicles (slight preference for fewer trips)
        # Not a hard constraint - we allow as many trips as needed
        for vehicle_id in range(self.num_vehicles):
            routing.SetFixedCostOfVehicle(50000, vehicle_id)

        # Search parameters
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = 120

        print(f"Solving VRP (time limit: 120s)...")
        solution = routing.SolveWithParameters(search_parameters)

        if solution:
            if self.verbose:
                print(f"\nVerbose: Solution found!")
                print(f"Verbose: Objective value: {solution.ObjectiveValue()}")
                print(f"Verbose: Number of vehicles used: {sum(1 for v in range(self.num_vehicles) if routing.IsVehicleUsed(solution, v))}")
                # Count visited sites
                visited = set()
                for vehicle_id in range(self.num_vehicles):
                    if routing.IsVehicleUsed(solution, vehicle_id):
                        index = routing.Start(vehicle_id)
                        while not routing.IsEnd(index):
                            node = manager.IndexToNode(index)
                            if node != 0:  # Not depot
                                visited.add(node)
                            index = solution.Value(routing.NextVar(index))
                print(f"Verbose: Sites visited: {len(visited)}/{len(self.sites)-1}")
                if len(visited) < len(self.sites) - 1:
                    unvisited = set(range(1, len(self.sites))) - visited
                    print(f"Verbose: Unvisited sites ({len(unvisited)}):")
                    for node in sorted(list(unvisited))[:20]:  # Show first 20
                        site = self.sites[node]
                        dist_from_home = self._haversine_distance(
                            self.home_base.lat, self.home_base.lon,
                            site.lat, site.lon
                        )
                        print(f"    {site.name:40s} - {dist_from_home:6.1f} mi from home")
                    if len(unvisited) > 20:
                        print(f"    ... and {len(unvisited) - 20} more")

            trips = self._extract_solution(manager, routing, solution, time_dimension)

            # Post-process: Resequence trips to fit operating hours constraints
            print(f"\nPost-processing: Resequencing trips to fit operating hours...")
            resequenced_trips = []
            all_rejected_sites = []

            for trip in trips:
                resequenced_trip, rejected_sites = self._resequence_trip_with_violations(trip)
                resequenced_trips.append(resequenced_trip)
                all_rejected_sites.extend(rejected_sites)

            if all_rejected_sites:
                print(f"\n✗ {len(all_rejected_sites)} site(s) could not be scheduled:")
                for site in all_rejected_sites:
                    print(f"  - {site['name']}: {site['reason']}")
            else:
                print(f"\n✓ All sites successfully scheduled within operating hours")

            # Store rejected sites for reporting
            self.rejected_sites = all_rejected_sites

            return resequenced_trips
        else:
            print(f"✗ No solution found!")
            return None

    def _extract_solution(self, manager, routing, solution, time_dimension):
        """Extract trips from solution with day-aware processing"""
        trips = []

        for vehicle_id in range(self.num_vehicles):
            index = routing.Start(vehicle_id)
            route_details = []
            total_distance = 0
            total_time = 0

            if routing.IsVehicleUsed(solution, vehicle_id):
                if self.verbose:
                    print(f"\nVerbose: Extracting Trip {vehicle_id + 1}")

                # Day-aware tracking (CRITICAL PARAMETERS)
                DAILY_BUDGET_MINUTES = self.hours_per_day * 60  # Parameterized day length
                VISIT_TIME_MINUTES = self.visit_minutes_per_site  # Parameterized visit time
                TRIP_START_HOUR = self.earliest_start_hour  # Earliest possible start (6am), but we prefer 9am

                if self.verbose:
                    print(f"  Daily budget: {DAILY_BUDGET_MINUTES} min ({self.hours_per_day} hrs)")
                    print(f"  Visit time per site: {VISIT_TIME_MINUTES} min")
                    print(f"  Trip starts at: {TRIP_START_HOUR:02d}:00")

                current_day = 1
                current_day_time_used = 0  # Minutes used in current day
                previous_site_coords = (self.home_base.lat, self.home_base.lon)  # (lat, lon)
                previous_arrival_minutes = 0

                # Process all nodes including return to depot
                while True:
                    node = manager.IndexToNode(index)
                    time_var = time_dimension.CumulVar(index)
                    arrival_minutes = solution.Min(time_var)

                    site = self.sites[node]

                    if self.verbose and node != 0:
                        print(f"\n  Processing site {len(route_details)}: {site.name}")
                        print(f"    Cumulative arrival: {arrival_minutes} min ({arrival_minutes/60:.2f} hrs)")

                    # Calculate travel time from previous stop
                    if node != 0:  # Not depot
                        # Calculate distance and travel time
                        travel_distance_miles = self._haversine_distance(
                            previous_site_coords[0], previous_site_coords[1],
                            site.lat, site.lon
                        )
                        travel_time_minutes = (travel_distance_miles / self.avg_speed_mph) * 60
                        visit_time_minutes = VISIT_TIME_MINUTES
                        time_needed = travel_time_minutes + visit_time_minutes

                        if self.verbose:
                            print(f"    Travel: {travel_distance_miles:.1f} mi, {travel_time_minutes:.1f} min")
                            print(f"    Visit: {visit_time_minutes} min")
                            print(f"    Total time needed: {time_needed:.1f} min ({time_needed/60:.2f} hrs)")
                            print(f"    Current day {current_day}: {current_day_time_used:.1f}/{DAILY_BUDGET_MINUTES} min used")

                        # Check if site fits in current day
                        if current_day_time_used + time_needed <= DAILY_BUDGET_MINUTES:
                            # Fits in current day
                            if self.verbose:
                                print(f"    ✓ Fits in day {current_day} ({current_day_time_used + time_needed:.1f}/{DAILY_BUDGET_MINUTES} min)")
                            current_day_time_used += time_needed
                            day_number = current_day
                            positioning_time = 0
                        else:
                            # Doesn't fit - use remaining time for positioning
                            positioning_time = DAILY_BUDGET_MINUTES - current_day_time_used
                            remaining_travel = max(0, travel_time_minutes - positioning_time)

                            if self.verbose:
                                print(f"    ✗ Doesn't fit in day {current_day}")
                                print(f"      Remaining in day {current_day}: {DAILY_BUDGET_MINUTES - current_day_time_used:.1f} min (positioning)")
                                print(f"      Remaining travel: {remaining_travel:.1f} min")
                                print(f"      Starting day {current_day + 1} with {remaining_travel + visit_time_minutes:.1f} min used")

                            # Start next day
                            current_day += 1
                            current_day_time_used = remaining_travel + visit_time_minutes
                            day_number = current_day

                            # Mark previous stop with positioning info
                            if route_details and route_details[-1].get('site_name') != 'Kirkwood, MO':
                                route_details[-1]['end_of_day_positioning'] = {
                                    'positioning_minutes': round(positioning_time, 1),
                                    'positioning_hours': round(positioning_time / 60, 2),
                                    'toward_site': site.name,
                                    'next_day_starts': current_day
                                }
                    else:
                        # Depot - no day assignment needed
                        day_number = current_day
                        travel_time_minutes = 0
                        positioning_time = 0

                    # Calculate actual wall-clock time based on ARRIVAL time (before visit)
                    # current_day_time_used includes travel + visit, so subtract visit for arrival time
                    if node != 0:  # Not depot - subtract visit time to get arrival
                        arrival_time_in_day = current_day_time_used - VISIT_TIME_MINUTES
                    else:  # Depot has no visit time
                        arrival_time_in_day = current_day_time_used

                    actual_minutes = int(TRIP_START_HOUR * 60 + arrival_time_in_day)
                    hour_of_day = (actual_minutes // 60) % 24
                    minute_of_hour = actual_minutes % 60

                    stop_info = {
                        'site': site.full_name,
                        'site_name': site.name,
                        'city': site.city,
                        'state': site.state,
                        'lat': site.lat,
                        'lon': site.lon,
                        'address': site.address,
                        'arrival_minutes': arrival_minutes,
                        'arrival_hours': round(arrival_minutes / 60, 2),
                        'day': day_number,
                        'day_time_used': round(current_day_time_used / 60, 2),  # Hours used so far this day
                        'time_of_day': f"{hour_of_day:02d}:{minute_of_hour:02d}"
                    }

                    # Flag if day exceeds preferred hours (soft limit)
                    if current_day_time_used / 60 > self.preferred_hours_per_day:
                        stop_info['exceeds_preferred_hours'] = True
                        stop_info['excess_hours'] = round(current_day_time_used / 60 - self.preferred_hours_per_day, 2)

                    # Update previous position for next iteration
                    previous_site_coords = (site.lat, site.lon)
                    previous_arrival_minutes = arrival_minutes

                    # Add operating hours info if available (skip for depot)
                    if node != 0 and hasattr(site, 'operating_hours') and site.operating_hours:
                        stop_info['operating_hours'] = {
                            'opens': f"{site.operating_hours.opens // 60:02d}:{site.operating_hours.opens % 60:02d}",
                            'closes': f"{site.operating_hours.closes // 60:02d}:{site.operating_hours.closes % 60:02d}",
                            'is_default': site.operating_hours.opens == 8*60 and site.operating_hours.closes == 17*60
                        }

                        # Include stamp availability flag
                        if hasattr(site, 'always_stamp_available'):
                            stop_info['always_stamp_available'] = site.always_stamp_available

                        # Check if arrival is within operating hours
                        # CRITICAL: Violations are NOT acceptable unless always_stamp_available
                        # RELAXED: Arrival must be during hours, but visit can extend past closing
                        arrival_hour_minutes = hour_of_day * 60 + minute_of_hour
                        if arrival_hour_minutes < site.operating_hours.opens or arrival_hour_minutes > site.operating_hours.closes:
                            warning_type = "INFO" if site.always_stamp_available else "VIOLATION"
                            stop_info['time_constraint_warning'] = f"[{warning_type}] Arrival at {hour_of_day:02d}:{minute_of_hour:02d} is outside operating hours ({site.operating_hours.opens//60:02d}:{site.operating_hours.opens%60:02d}-{site.operating_hours.closes//60:02d}:{site.operating_hours.closes%60:02d})"
                            if not site.always_stamp_available:
                                stop_info['invalid_visit'] = True  # Mark as requiring manual adjustment

                    route_details.append(stop_info)

                    # Break if this is the end node
                    if routing.IsEnd(index):
                        break

                    previous_index = index
                    index = solution.Value(routing.NextVar(index))
                    if not routing.IsEnd(index):
                        total_distance += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)

                # Get final time
                final_time_var = time_dimension.CumulVar(index)
                total_time = solution.Min(final_time_var)

                if len(route_details) > 1:  # More than just depot
                    # Post-process: Calculate optimal start time for EACH DAY and handle timezones

                    # Group stops by day (excluding depot)
                    days_map = {}  # day_number -> list of stops
                    for stop in route_details:
                        if 'day' in stop and stop.get('site') != self.home_base.name:
                            day_num = stop['day']
                            if day_num not in days_map:
                                days_map[day_num] = []
                            days_map[day_num].append(stop)

                    # Build map of when each day starts in cumulative minutes
                    day_start_cumulative = {}
                    day_start_cumulative[1] = 0  # Day 1 starts at minute 0

                    # For subsequent days, find where they start
                    for day_num in sorted(days_map.keys()):
                        if day_num > 1 and day_num not in day_start_cumulative:
                            # Find last stop of previous day
                            prev_day_stops = days_map.get(day_num - 1, [])
                            if prev_day_stops:
                                last_stop = prev_day_stops[-1]
                                # Day starts after previous day's budget
                                # Calculate based on when previous day started + full day budget
                                prev_day_start = day_start_cumulative.get(day_num - 1, 0)
                                day_start_cumulative[day_num] = prev_day_start + DAILY_BUDGET_MINUTES
                            else:
                                # Fallback: use day 1 start + (day_num - 1) * daily budget
                                day_start_cumulative[day_num] = (day_num - 1) * DAILY_BUDGET_MINUTES

                    # For each day, recalculate times with optimal start and timezone
                    for day_num in sorted(days_map.keys()):
                        day_stops = days_map[day_num]
                        if not day_stops:
                            continue

                        first_site_stop = day_stops[0]

                        # Determine starting point for this day
                        if day_num == 1:
                            # Day 1 starts from home base
                            depot_stop = route_details[0]
                        else:
                            # Day 2+ starts from last stop of previous day
                            prev_day_stops = days_map.get(day_num - 1, [])
                            if prev_day_stops:
                                depot_stop = prev_day_stops[-1]
                            else:
                                # Fallback to home base
                                depot_stop = route_details[0]

                        # Create temporary route_details for this day (start point + first site)
                        temp_route = [depot_stop, first_site_stop]

                        # Calculate optimal start for this day
                        optimal_start_hour = self._calculate_optimal_start_hour(temp_route)

                        # Get when this day starts in cumulative minutes
                        day_start_minutes = day_start_cumulative.get(day_num, 0)

                        if self.verbose:
                            print(f"\nVerbose: Adjusting Trip {vehicle_id + 1}, Day {day_num} start time")
                            print(f"  First site: {first_site_stop.get('site_name', 'Unknown')}")
                            print(f"  Optimal start: {optimal_start_hour:02d}:00")
                            print(f"  Day starts at cumulative minute: {day_start_minutes}")
                            print(f"  First site cumulative arrival: {first_site_stop['arrival_minutes']} min")

                        # Recalculate time_of_day for ALL stops on this day (excluding depot)
                        for stop in route_details:
                            if stop.get('day') == day_num and stop.get('site') != self.home_base.name:
                                # Get site for timezone lookup
                                site_lat = stop['lat']
                                site_lon = stop['lon']
                                site = Site(name=stop['site_name'], lat=site_lat, lon=site_lon)

                                # Calculate minutes into this day using day start time
                                minutes_into_day = stop['arrival_minutes'] - day_start_minutes

                                # Calculate actual time of day based on optimal start
                                total_minutes = optimal_start_hour * 60 + minutes_into_day
                                hour_of_day = (total_minutes // 60) % 24
                                minute_of_hour = total_minutes % 60

                                # Update time_of_day with recalculated time
                                stop['time_of_day'] = f"{hour_of_day:02d}:{minute_of_hour:02d}"

                                # Add timezone information
                                tz_name = site.get_timezone()
                                stop['timezone'] = tz_name

                                # Recalculate operating hours violations with new times
                                if 'operating_hours' in stop and stop['operating_hours']:
                                    op_hours = stop['operating_hours']
                                    arrival_hour_minutes = hour_of_day * 60 + minute_of_hour

                                    # Parse operating hours
                                    opens_str = op_hours['opens']
                                    closes_str = op_hours['closes']

                                    if ':' in opens_str:
                                        opens_parts = opens_str.split(':')
                                        opens_minutes = int(opens_parts[0]) * 60 + int(opens_parts[1])
                                    else:
                                        opens_minutes = 9 * 60  # Default 9am

                                    if ':' in closes_str:
                                        closes_parts = closes_str.split(':')
                                        closes_minutes = int(closes_parts[0]) * 60 + int(closes_parts[1])
                                    else:
                                        closes_minutes = 17 * 60  # Default 5pm

                                    # Check if arrival is within operating hours
                                    if arrival_hour_minutes < opens_minutes or arrival_hour_minutes > closes_minutes:
                                        always_available = stop.get('always_stamp_available', False)
                                        warning_type = "INFO" if always_available else "VIOLATION"
                                        stop['time_constraint_warning'] = f"[{warning_type}] Arrival at {hour_of_day:02d}:{minute_of_hour:02d} {tz_name} is outside operating hours ({opens_str}-{closes_str})"
                                        if not always_available:
                                            stop['invalid_visit'] = True
                                    else:
                                        # Remove violation if it now fits
                                        stop.pop('time_constraint_warning', None)
                                        stop.pop('invalid_visit', None)

                    trips.append({
                        'trip_number': vehicle_id + 1,
                        'route_details': route_details,
                        'stats': {
                            'total_sites': len(route_details) - 1,
                            'total_distance_miles': round(total_distance / 1609.34, 1),
                            'total_time_hours': round(total_time / 60, 2),
                            'total_days': round(total_time / (self.hours_per_day * 60), 2),
                            'within_target': total_time <= self.target_trip_minutes,
                            'within_max': total_time <= self.max_trip_minutes
                        }
                    })

        return trips


def load_nps_sites(home_base: Tuple[float, float], max_distance_miles: float = None):
    """Load NPS sites from ambers-data.md files, optionally filtered by distance"""
    print("Loading NPS sites from ambers-data.md files...")

    # Load all sites using NPSDataLoader
    loader = NPSDataLoader()
    all_sites = loader.load_all_sites()

    def haversine(lat1, lon1, lat2, lon2):
        R = 3959
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        return R * 2 * math.asin(math.sqrt(a))

    sites = []
    home_lat, home_lon = home_base

    for nps_site in all_sites.values():
        # Filter by distance if specified
        if max_distance_miles:
            dist = haversine(home_lat, home_lon, nps_site.lat, nps_site.lon)
            if dist > max_distance_miles:
                continue

        sites.append(Site(
            name=nps_site.name,
            lat=nps_site.lat,
            lon=nps_site.lon,
            address=nps_site.address,
            city=nps_site.city,
            state=nps_site.state,
            operating_hours=nps_site.operating_hours,
            always_stamp_available=nps_site.always_stamp_available
        ))

    return sites


def main():
    """Generate multi-trip itineraries with configurable parameters"""
    parser = argparse.ArgumentParser(description='VRP Trip Planner for NPS sites')
    parser.add_argument('--home', default=DEFAULT_HOME_NAME, help='Home base location name')
    parser.add_argument('--lat', type=float, default=DEFAULT_HOME_LAT, help='Home base latitude')
    parser.add_argument('--lon', type=float, default=DEFAULT_HOME_LON, help='Home base longitude')
    parser.add_argument('--target-days', type=int, default=3,
                        help='Target days per trip (any positive integer)')
    parser.add_argument('--max-days', type=int, help='Max days per trip (defaults to target+1)')
    parser.add_argument('--max-distance', type=int, default=500,
                        help='Maximum distance from home base in miles (default: 500, use 0 for all sites)')
    parser.add_argument('--visit-hours', type=float, default=2.0,
                        help='Hours to spend at each site (default: 2.0)')
    parser.add_argument('--hours-per-day', type=int, default=15,
                        help='Maximum working hours per day, 06:00-21:00 (default: 15)')
    parser.add_argument('--preferred-hours-per-day', type=int, default=12,
                        help='Preferred hours per day, exceeding this incurs penalties (default: 12)')
    parser.add_argument('--avg-speed', type=float, default=55.0,
                        help='Average driving speed in mph (default: 55)')
    parser.add_argument('--no-prioritize-range', action='store_true',
                        help='Disable range prioritization (default: range prioritization is enabled)')
    parser.add_argument('--output', default='vrp_trip_itineraries.yaml', help='Output file (.json or .yaml)')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose debug logging to understand VRP solver decisions')

    args = parser.parse_args()

    # Set max days if not specified
    max_days = args.max_days if args.max_days else args.target_days + 1

    print("="*70)
    print(f"VRP TRIP PLANNER FROM {args.home.upper()}")
    print("="*70)
    print(f"Home base: {args.home} ({args.lat}, {args.lon})")
    print(f"Trip length: {args.target_days} days (max {max_days})")
    print(f"Max distance: {args.max_distance} miles" if args.max_distance > 0 else "Max distance: unlimited")
    print(f"Time per site: {args.visit_hours} hours")
    print(f"Working hours per day: {args.hours_per_day} hours (~{int(args.hours_per_day / args.visit_hours)} sites/day)")
    print(f"Average speed: {args.avg_speed} mph")
    print()

    max_dist = args.max_distance if args.max_distance > 0 else None
    sites = load_nps_sites((args.lat, args.lon), max_distance_miles=max_dist)
    print(f"Loaded {len(sites)} sites")

    planner = VRPTripPlanner(
        sites=sites,
        home_base=(args.home, args.lat, args.lon),
        visit_hours_per_site=args.visit_hours,
        hours_per_day=args.hours_per_day,
        preferred_hours_per_day=args.preferred_hours_per_day,
        target_trip_days=args.target_days,
        max_trip_days=max_days,
        avg_speed_mph=args.avg_speed,
        prioritize_range=not args.no_prioritize_range,
        verbose=args.verbose
    )

    trips = planner.solve()

    if trips:
        # Add map links to each trip
        for trip in trips:
            waypoints = [(stop['lat'], stop['lon']) for stop in trip['route_details']]
            trip['map_links'] = {
                'openstreetmap_route': create_osm_route_link(waypoints),
                'google_maps_route': create_google_maps_link(waypoints)
            }

        # Generate site coverage report
        visited_sites = set()
        for trip in trips:
            for stop in trip['route_details']:
                site_name = stop.get('site_name', '')
                # Exclude home base from visited sites
                if site_name != args.home and site_name:
                    visited_sites.add(site_name)

        all_site_names = {site.name for site in sites}
        skipped_sites = all_site_names - visited_sites

        coverage_report = {
            'total_sites_in_radius': len(sites),
            'sites_visited': len(visited_sites),
            'sites_skipped': len(skipped_sites),
            'all_sites_covered': len(skipped_sites) == 0
        }

        if skipped_sites or hasattr(planner, 'rejected_sites'):
            # For each skipped site, determine reason
            skipped_details = []

            # Add rejected sites (operating hours violations) first
            if hasattr(planner, 'rejected_sites'):
                for rejected_site in planner.rejected_sites:
                    skipped_details.append({
                        'name': rejected_site['name'],
                        'reason': f"Operating hours violation: {rejected_site.get('reason', 'Unknown')}",
                        'attempted_arrival': rejected_site.get('attempted_arrival'),
                        'operating_hours': rejected_site.get('operating_hours'),
                        'lat': rejected_site.get('lat'),
                        'lon': rejected_site.get('lon')
                    })

            # Add sites that weren't included in solution at all
            for site_name in sorted(skipped_sites):
                # Skip if already in rejected sites
                if hasattr(planner, 'rejected_sites') and any(r['name'] == site_name for r in planner.rejected_sites):
                    continue

                # Find the site object
                site_obj = next((s for s in sites if s.name == site_name), None)
                if site_obj:
                    # Default reason - typically shouldn't happen with VRP solver
                    reason = "Could not fit within trip constraints (time/distance limitations)"
                    skipped_details.append({
                        'name': site_name,
                        'reason': reason,
                        'lat': site_obj.lat,
                        'lon': site_obj.lon
                    })

            if skipped_details:
                coverage_report['skipped_sites'] = skipped_details

        output = {
            'home_base': {'name': args.home, 'lat': args.lat, 'lon': args.lon},
            'parameters': {
                'visit_hours_per_site': args.visit_hours,
                'hours_per_day': args.hours_per_day,
                'preferred_hours_per_day': args.preferred_hours_per_day,
                'target_days_per_trip': args.target_days,
                'max_days_per_trip': max_days,
                'avg_speed_mph': args.avg_speed
            },
            'coverage': coverage_report,
            'trips': trips,
            'summary': {
                'total_trips': len(trips),
                'total_sites': sum(t['stats']['total_sites'] for t in trips),
                'total_distance_miles': sum(t['stats']['total_distance_miles'] for t in trips),
                'total_days': sum(t['stats']['total_days'] for t in trips)
            }
        }

        output_file = Path(args.output)

        # Determine format based on file extension
        if output_file.suffix.lower() in ['.yaml', '.yml']:
            with open(output_file, 'w') as f:
                yaml.dump(output, f, default_flow_style=False, sort_keys=False, width=120)
        else:
            with open(output_file, 'w') as f:
                json.dump(output, f, indent=2)

        # Create GeoJSON files for map visualization
        geojson_dir = output_file.parent / "geojson"
        geojson_dir.mkdir(exist_ok=True)
        for trip in trips:
            geojson_file = geojson_dir / f"trip_{trip['trip_number']}.geojson"
            with open(geojson_file, 'w') as f:
                json.dump(create_geojson_route(trip), f, indent=2)

        print(f"\n{'='*70}")
        print(f"RESULTS")
        print(f"{'='*70}")
        print(f"Total trips: {output['summary']['total_trips']}")
        print(f"Total sites visited: {output['summary']['total_sites']}/{len(sites)}")
        print(f"Total distance: {output['summary']['total_distance_miles']:,.0f} miles")
        print(f"Total trip days: {output['summary']['total_days']:.1f}")

        # Site coverage report
        print(f"\n{'='*70}")
        print(f"SITE COVERAGE REPORT")
        print(f"{'='*70}")
        coverage = output['coverage']
        if coverage['all_sites_covered']:
            print(f"✓ All {coverage['total_sites_in_radius']} sites within radius are included in the solution")
        else:
            print(f"⚠ {coverage['sites_visited']} of {coverage['total_sites_in_radius']} sites included")
            print(f"\nSkipped sites ({coverage['sites_skipped']}):")
            for site in coverage.get('skipped_sites', []):
                print(f"  - {site['name']}")
                print(f"    Reason: {site['reason']}")
                print(f"    Location: ({site['lat']}, {site['lon']})")

        print(f"\nPer-trip breakdown:")
        for trip in trips:
            stats = trip['stats']
            status = "✓ Target" if stats['within_target'] else ("✓ Max" if stats['within_max'] else "✗ Over")
            print(f"  Trip {trip['trip_number']}: {stats['total_sites']} sites, {stats['total_days']:.1f} days, {stats['total_distance_miles']:.0f} mi {status}")

        print(f"\n✓ Saved to {output_file}")
        print(f"✓ GeoJSON files: {geojson_dir}/")
        print(f"\nYou can:")
        print(f"  1. Open {output_file} to see trip details with map links")
        print(f"  2. Upload GeoJSON files to http://geojson.io to visualize routes")
        print(f"  3. Use the OpenStreetMap/Google Maps links from the YAML file")
        print(f"\nExample usage for other configurations:")
        print(f"  # 1-week trips:")
        print(f"  python3 {__file__} --target-days 7 --output weekly_trips.yaml")
        print(f"  # 2-week trips:")
        print(f"  python3 {__file__} --target-days 14 --output biweekly_trips.yaml")
        print(f"  # Different home base:")
        print(f"  python3 {__file__} --home 'Denver, CO' --lat 39.7392 --lon -104.9903")
    else:
        print("\n✗ No solution found")


if __name__ == '__main__':
    main()
