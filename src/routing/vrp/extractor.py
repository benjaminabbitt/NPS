#!/usr/bin/env python3
"""
Trip Extractor

Extracts trip solutions from OR-Tools VRP solver and formats them
with day-aware processing, operating hours checks, and timezone handling.
"""

from typing import List, Dict, Any, Tuple, Callable
from core.site import Site


class TripExtractor:
    """
    Extracts and formats VRP solution into trip objects.

    Handles:
    - Day-aware time tracking
    - Operating hours validation
    - Timezone conversions
    - Optimal start time calculation per day
    """

    def __init__(
        self,
        sites: List[Site],
        home_base: Site,
        num_vehicles: int,
        hours_per_day: int,
        preferred_hours_per_day: int,
        visit_minutes_per_site: int,
        target_trip_minutes: int,
        max_trip_minutes: int,
        avg_speed_mph: float,
        earliest_start_hour: int,
        preferred_start_hour: int,
        haversine_fn: Callable,
        calculate_optimal_start_hour_fn: Callable,
        verbose: bool = False
    ):
        """Initialize trip extractor with configuration"""
        self.sites = sites
        self.home_base = home_base
        self.num_vehicles = num_vehicles
        self.hours_per_day = hours_per_day
        self.preferred_hours_per_day = preferred_hours_per_day
        self.visit_minutes_per_site = visit_minutes_per_site
        self.target_trip_minutes = target_trip_minutes
        self.max_trip_minutes = max_trip_minutes
        self.avg_speed_mph = avg_speed_mph
        self.earliest_start_hour = earliest_start_hour
        self.preferred_start_hour = preferred_start_hour
        self.haversine_fn = haversine_fn
        self.calculate_optimal_start_hour_fn = calculate_optimal_start_hour_fn
        self.verbose = verbose

    def extract_solution(self, manager, routing, solution, time_dimension) -> List[Dict[str, Any]]:
        """Extract trips from OR-Tools solution with day-aware processing"""
        trips = []

        for vehicle_id in range(self.num_vehicles):
            if routing.IsVehicleUsed(solution, vehicle_id):
                trip = self._extract_vehicle_trip(
                    vehicle_id,
                    manager,
                    routing,
                    solution,
                    time_dimension
                )
                if trip:
                    trips.append(trip)

        return trips

    def _extract_vehicle_trip(
        self,
        vehicle_id: int,
        manager,
        routing,
        solution,
        time_dimension
    ) -> Dict[str, Any]:
        """Extract a single vehicle's trip"""
        if self.verbose:
            print(f"\nVerbose: Extracting Trip {vehicle_id + 1}")

        index = routing.Start(vehicle_id)
        route_details = []
        total_distance = 0

        # Day tracking
        daily_budget_minutes = self.hours_per_day * 60
        current_day = 1
        current_day_time_used = 0
        previous_site_coords = (self.home_base.lat, self.home_base.lon)

        # Process all nodes including return to depot
        while True:
            node = manager.IndexToNode(index)
            time_var = time_dimension.CumulVar(index)
            arrival_minutes = solution.Min(time_var)
            site = self.sites[node]

            if node != 0:  # Not depot
                stop_info, day_metrics = self._process_site_stop(
                    site,
                    node,
                    arrival_minutes,
                    previous_site_coords,
                    current_day,
                    current_day_time_used,
                    daily_budget_minutes,
                    route_details
                )

                current_day = day_metrics['current_day']
                current_day_time_used = day_metrics['current_day_time_used']
                previous_site_coords = (site.lat, site.lon)
                route_details.append(stop_info)
            else:
                # Depot
                stop_info = self._create_depot_stop(
                    site,
                    arrival_minutes,
                    current_day,
                    current_day_time_used
                )
                route_details.append(stop_info)

            # Break if this is the end node
            if routing.IsEnd(index):
                break

            previous_index = index
            index = solution.Value(routing.NextVar(index))
            if not routing.IsEnd(index):
                total_distance += routing.GetArcCostForVehicle(
                    previous_index,
                    index,
                    vehicle_id
                )

        # Get final time
        final_time_var = time_dimension.CumulVar(index)
        total_time = solution.Min(final_time_var)

        # Post-process: Calculate optimal start time for each day
        if len(route_details) > 1:
            self._post_process_day_times(
                route_details,
                daily_budget_minutes,
                vehicle_id
            )

        return {
            'trip_number': vehicle_id + 1,
            'route_details': route_details,
            'stats': {
                'total_sites': len(route_details) - 2,  # Exclude start/end depot
                'total_distance_miles': round(total_distance / 1609.34, 1),
                'total_time_hours': round(total_time / 60, 2),
                'total_days': round(total_time / (self.hours_per_day * 60), 2),
                'within_target': total_time <= self.target_trip_minutes,
                'within_max': total_time <= self.max_trip_minutes
            }
        }

    def _process_site_stop(
        self,
        site: Site,
        node: int,
        arrival_minutes: int,
        previous_coords: Tuple[float, float],
        current_day: int,
        current_day_time_used: float,
        daily_budget_minutes: int,
        route_details: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Process a non-depot site stop"""
        if self.verbose:
            print(f"\n  Processing site {len(route_details)}: {site.name}")
            print(f"    Cumulative arrival: {arrival_minutes} min ({arrival_minutes/60:.2f} hrs)")

        # Calculate travel and visit time
        travel_distance = self.haversine_fn(
            previous_coords[0], previous_coords[1],
            site.lat, site.lon
        )
        travel_time = (travel_distance / self.avg_speed_mph) * 60
        visit_time = self.visit_minutes_per_site
        time_needed = travel_time + visit_time

        if self.verbose:
            print(f"    Travel: {travel_distance:.1f} mi, {travel_time:.1f} min")
            print(f"    Visit: {visit_time} min")
            print(f"    Total time needed: {time_needed:.1f} min")
            print(f"    Current day {current_day}: {current_day_time_used:.1f}/{daily_budget_minutes} min used")

        # Check if site fits in current day
        day_number, new_day_time_used, positioning_time = self._calculate_day_assignment(
            time_needed,
            current_day,
            current_day_time_used,
            daily_budget_minutes,
            travel_time,
            visit_time
        )

        # Mark positioning info on previous stop if we rolled to next day
        if day_number > current_day and route_details:
            self._mark_positioning(
                route_details[-1],
                positioning_time,
                site.name,
                day_number
            )

        # Create stop info
        stop_info = self._create_stop_info(
            site,
            arrival_minutes,
            day_number,
            new_day_time_used
        )

        # Check operating hours
        self._check_operating_hours(stop_info, site)

        # Flag if day exceeds preferred hours
        if new_day_time_used / 60 > self.preferred_hours_per_day:
            stop_info['exceeds_preferred_hours'] = True
            stop_info['excess_hours'] = round(
                new_day_time_used / 60 - self.preferred_hours_per_day,
                2
            )

        day_metrics = {
            'current_day': day_number,
            'current_day_time_used': new_day_time_used
        }

        return stop_info, day_metrics

    def _calculate_day_assignment(
        self,
        time_needed: float,
        current_day: int,
        current_day_time_used: float,
        daily_budget: int,
        travel_time: float,
        visit_time: float
    ) -> Tuple[int, float, float]:
        """Calculate which day a site belongs to and time usage"""
        if current_day_time_used + time_needed <= daily_budget:
            # Fits in current day
            if self.verbose:
                new_usage = current_day_time_used + time_needed
                print(f"    ✓ Fits in day {current_day} ({new_usage:.1f}/{daily_budget} min)")
            return current_day, current_day_time_used + time_needed, 0
        else:
            # Doesn't fit - use remaining time for positioning
            positioning_time = daily_budget - current_day_time_used
            remaining_travel = max(0, travel_time - positioning_time)

            if self.verbose:
                print(f"    ✗ Doesn't fit in day {current_day}")
                print(f"      Remaining in day {current_day}: {daily_budget - current_day_time_used:.1f} min (positioning)")
                print(f"      Remaining travel: {remaining_travel:.1f} min")
                print(f"      Starting day {current_day + 1} with {remaining_travel + visit_time:.1f} min used")

            return (
                current_day + 1,
                remaining_travel + visit_time,
                positioning_time
            )

    def _mark_positioning(
        self,
        previous_stop: Dict[str, Any],
        positioning_time: float,
        toward_site: str,
        next_day: int
    ):
        """Mark previous stop with end-of-day positioning info"""
        if previous_stop.get('site_name') != self.home_base.name:
            previous_stop['end_of_day_positioning'] = {
                'positioning_minutes': round(positioning_time, 1),
                'positioning_hours': round(positioning_time / 60, 2),
                'toward_site': toward_site,
                'next_day_starts': next_day
            }

    def _create_stop_info(
        self,
        site: Site,
        arrival_minutes: int,
        day_number: int,
        day_time_used: float
    ) -> Dict[str, Any]:
        """Create stop info dictionary"""
        # Calculate arrival time of day
        arrival_time_in_day = day_time_used - self.visit_minutes_per_site
        actual_minutes = int(self.earliest_start_hour * 60 + arrival_time_in_day)
        hour = (actual_minutes // 60) % 24
        minute = actual_minutes % 60

        return {
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
            'day_time_used': round(day_time_used / 60, 2),
            'time_of_day': f"{hour:02d}:{minute:02d}"
        }

    def _create_depot_stop(
        self,
        site: Site,
        arrival_minutes: int,
        current_day: int,
        current_day_time_used: float
    ) -> Dict[str, Any]:
        """Create depot stop info"""
        actual_minutes = int(self.earliest_start_hour * 60 + current_day_time_used)
        hour = (actual_minutes // 60) % 24
        minute = actual_minutes % 60

        return {
            'site': site.full_name,
            'site_name': site.name,
            'city': site.city,
            'state': site.state,
            'lat': site.lat,
            'lon': site.lon,
            'address': site.address,
            'arrival_minutes': arrival_minutes,
            'arrival_hours': round(arrival_minutes / 60, 2),
            'day': current_day,
            'day_time_used': round(current_day_time_used / 60, 2),
            'time_of_day': f"{hour:02d}:{minute:02d}"
        }

    def _check_operating_hours(self, stop_info: Dict[str, Any], site: Site):
        """Check and annotate operating hours constraints"""
        if not hasattr(site, 'operating_hours') or not site.operating_hours:
            return

        stop_info['operating_hours'] = {
            'opens': f"{site.operating_hours.opens // 60:02d}:{site.operating_hours.opens % 60:02d}",
            'closes': f"{site.operating_hours.closes // 60:02d}:{site.operating_hours.closes % 60:02d}",
            'is_default': (
                site.operating_hours.opens == 8*60 and
                site.operating_hours.closes == 17*60
            )
        }

        if hasattr(site, 'always_stamp_available'):
            stop_info['always_stamp_available'] = site.always_stamp_available

        # Check arrival time against operating hours
        time_parts = stop_info['time_of_day'].split(':')
        arrival_hour_min = int(time_parts[0]) * 60 + int(time_parts[1])

        if arrival_hour_min > site.operating_hours.closes:
            warning_type = "INFO" if site.always_stamp_available else "VIOLATION"
            stop_info['time_constraint_warning'] = (
                f"[{warning_type}] Arrival at {stop_info['time_of_day']} is outside "
                f"operating hours ({stop_info['operating_hours']['opens']}-{stop_info['operating_hours']['closes']})"
            )
            if not site.always_stamp_available:
                stop_info['invalid_visit'] = True
        elif arrival_hour_min < site.operating_hours.opens:
            stop_info['time_constraint_info'] = (
                f"[INFO] Early arrival at {stop_info['time_of_day']}, "
                f"site opens at {stop_info['operating_hours']['opens']}"
            )

    def _post_process_day_times(
        self,
        route_details: List[Dict[str, Any]],
        daily_budget: int,
        vehicle_id: int
    ):
        """Post-process to calculate optimal start time for each day and handle timezones"""
        # Group stops by day
        days_map = {}
        for stop in route_details:
            if 'day' in stop and stop.get('site') != self.home_base.name:
                day_num = stop['day']
                if day_num not in days_map:
                    days_map[day_num] = []
                days_map[day_num].append(stop)

        # Calculate when each day starts
        day_start_cumulative = {1: 0}
        for day_num in sorted(days_map.keys()):
            if day_num > 1 and day_num not in day_start_cumulative:
                prev_day_stops = days_map.get(day_num - 1, [])
                if prev_day_stops:
                    prev_day_start = day_start_cumulative.get(day_num - 1, 0)
                    day_start_cumulative[day_num] = prev_day_start + daily_budget
                else:
                    day_start_cumulative[day_num] = (day_num - 1) * daily_budget

        # Recalculate times for each day with optimal start and timezone
        for day_num in sorted(days_map.keys()):
            self._recalculate_day_times(
                route_details,
                days_map,
                day_num,
                day_start_cumulative,
                vehicle_id
            )

    def _recalculate_day_times(
        self,
        route_details: List[Dict[str, Any]],
        days_map: Dict[int, List[Dict[str, Any]]],
        day_num: int,
        day_start_cumulative: Dict[int, int],
        vehicle_id: int
    ):
        """Recalculate times for a specific day"""
        day_stops = days_map[day_num]
        if not day_stops:
            return

        first_site_stop = day_stops[0]

        # Determine starting point for this day
        if day_num == 1:
            depot_stop = route_details[0]
        else:
            prev_day_stops = days_map.get(day_num - 1, [])
            depot_stop = prev_day_stops[-1] if prev_day_stops else route_details[0]

        # Calculate optimal start for this day
        temp_route = [depot_stop, first_site_stop]
        optimal_start_hour = self.calculate_optimal_start_hour_fn(temp_route)

        day_start_minutes = day_start_cumulative.get(day_num, 0)

        if self.verbose:
            print(f"\nVerbose: Adjusting Trip {vehicle_id + 1}, Day {day_num} start time")
            print(f"  First site: {first_site_stop.get('site_name', 'Unknown')}")
            print(f"  Optimal start: {optimal_start_hour:02d}:00")

        # Recalculate time_of_day for all stops on this day
        for stop in route_details:
            if stop.get('day') == day_num and stop.get('site') != self.home_base.name:
                self._update_stop_time(stop, day_start_minutes, optimal_start_hour)

    def _update_stop_time(
        self,
        stop: Dict[str, Any],
        day_start_minutes: int,
        optimal_start_hour: int
    ):
        """Update a stop's time and timezone information"""
        # Create Site for timezone lookup
        site = Site(
            name=stop['site_name'],
            lat=stop['lat'],
            lon=stop['lon']
        )

        # Calculate time of day
        minutes_into_day = stop['arrival_minutes'] - day_start_minutes
        total_minutes = optimal_start_hour * 60 + minutes_into_day
        hour = (total_minutes // 60) % 24
        minute = total_minutes % 60

        stop['time_of_day'] = f"{hour:02d}:{minute:02d}"
        stop['timezone'] = site.get_timezone()

        # Recalculate operating hours violations with new times
        self._recheck_operating_hours(stop, hour, minute)

    def _recheck_operating_hours(
        self,
        stop: Dict[str, Any],
        hour: int,
        minute: int
    ):
        """Recheck operating hours with updated times"""
        if 'operating_hours' not in stop or not stop['operating_hours']:
            return

        op_hours = stop['operating_hours']
        arrival_minutes = hour * 60 + minute

        # Parse operating hours
        opens_minutes = self._parse_time_string(op_hours['opens'], 9 * 60)
        closes_minutes = self._parse_time_string(op_hours['closes'], 17 * 60)

        # Check constraints
        always_available = stop.get('always_stamp_available', False)
        tz_name = stop.get('timezone', '')

        if arrival_minutes > closes_minutes:
            warning_type = "INFO" if always_available else "VIOLATION"
            stop['time_constraint_warning'] = (
                f"[{warning_type}] Arrival at {hour:02d}:{minute:02d} {tz_name} "
                f"is outside operating hours ({op_hours['opens']}-{op_hours['closes']})"
            )
            if not always_available:
                stop['invalid_visit'] = True
        elif arrival_minutes < opens_minutes:
            stop['time_constraint_info'] = (
                f"[INFO] Early arrival at {hour:02d}:{minute:02d} {tz_name}, "
                f"site opens at {op_hours['opens']}"
            )
            stop.pop('time_constraint_warning', None)
            stop.pop('invalid_visit', None)
        else:
            # Within hours - clear all warnings
            stop.pop('time_constraint_warning', None)
            stop.pop('time_constraint_info', None)
            stop.pop('invalid_visit', None)

    def _parse_time_string(self, time_str: str, default: int) -> int:
        """Parse time string to minutes since midnight"""
        if ':' in time_str:
            parts = time_str.split(':')
            return int(parts[0]) * 60 + int(parts[1])
        return default
