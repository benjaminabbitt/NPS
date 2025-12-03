#!/usr/bin/env python3
"""
Trip Validator

Validates and resequences trips to satisfy operating hours constraints.
Rejects sites that cannot fit within trip day limits.
"""

from typing import List, Dict, Tuple, Any, Callable
from core.site import Site


class TripValidator:
    """
    Validates trips and resequences sites to fit operating hours.

    Strategy:
    1. Take sites in VRP order
    2. Try to fit each into current day
    3. If doesn't fit, try reordering current day
    4. If reordering works, use it
    5. If not, move to next day
    """

    def __init__(
        self,
        home_base: Site,
        hours_per_day: int,
        visit_minutes_per_site: int,
        max_trip_minutes: int,
        target_trip_minutes: int,
        avg_speed_mph: float,
        haversine_fn: Callable,
        check_site_fits_fn: Callable,
        calculate_optimal_start_hour_fn: Callable,
        try_reorder_fn: Callable,
        verbose: bool = False
    ):
        """
        Initialize trip validator.

        Args:
            home_base: Home base site (depot)
            hours_per_day: Hours per day (hard maximum)
            visit_minutes_per_site: Time to spend at each site
            max_trip_minutes: Maximum trip duration
            target_trip_minutes: Target trip duration
            avg_speed_mph: Average travel speed
            haversine_fn: Function to calculate distance
            check_site_fits_fn: Function to check if site fits in day
            calculate_optimal_start_hour_fn: Function to calculate optimal start time
            try_reorder_fn: Function to try reordering sites
            verbose: Print detailed logging
        """
        self.home_base = home_base
        self.hours_per_day = hours_per_day
        self.visit_minutes_per_site = visit_minutes_per_site
        self.max_trip_minutes = max_trip_minutes
        self.target_trip_minutes = target_trip_minutes
        self.avg_speed_mph = avg_speed_mph
        self.haversine_fn = haversine_fn
        self.check_site_fits_fn = check_site_fits_fn
        self.calculate_optimal_start_hour_fn = calculate_optimal_start_hour_fn
        self.try_reorder_fn = try_reorder_fn
        self.verbose = verbose

    def resequence_trip(self, trip: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Resequence trip sites to fit operating hours constraints.

        Args:
            trip: Trip dictionary with 'route_details' and 'trip_number'

        Returns:
            (resequenced_trip, rejected_sites)
        """
        route_details = trip['route_details']
        rejected_sites = []

        # Extract non-depot sites
        sites_to_schedule = [
            stop for stop in route_details
            if stop.get('site_name') != self.home_base.name
        ]

        if not sites_to_schedule:
            return trip, []

        # Build days
        daily_budget_minutes = self.hours_per_day * 60
        days = []
        current_day_sites = []
        start_location = (self.home_base.lat, self.home_base.lon)

        if self.verbose:
            print(f"\nResequencing Trip {trip['trip_number']}:")

        for i, site in enumerate(sites_to_schedule):
            result = self._schedule_site(
                site,
                i,
                len(sites_to_schedule),
                current_day_sites,
                days,
                start_location,
                daily_budget_minutes
            )

            if result['action'] == 'added':
                current_day_sites = result['current_day_sites']
            elif result['action'] == 'new_day':
                days.append(current_day_sites)
                current_day_sites = result['current_day_sites']
                start_location = result['start_location']
            elif result['action'] == 'rejected':
                rejected_sites.append(result['rejected_site'])
                current_day_sites = result['current_day_sites']
            elif result['action'] == 'reordered':
                current_day_sites = result['current_day_sites']
                if result.get('update_prev_day') and days:
                    days[-1].extend(result['moved_to_prev'])

        # Add last day if it has sites
        if current_day_sites:
            days.append(current_day_sites)

        # Rebuild route with resequenced sites
        return self._build_resequenced_trip(
            trip,
            days,
            route_details,
            rejected_sites
        )

    def _schedule_site(
        self,
        site: Dict[str, Any],
        site_index: int,
        total_sites: int,
        current_day_sites: List[Dict[str, Any]],
        days: List[List[Dict[str, Any]]],
        start_location: Tuple[float, float],
        daily_budget_minutes: int
    ) -> Dict[str, Any]:
        """
        Try to schedule a single site into the trip.

        Returns dict with 'action' key indicating what happened:
        - 'added': Site was added to current day
        - 'new_day': Started new day with this site
        - 'rejected': Site was rejected
        - 'reordered': Sites were reordered to fit site
        """
        # Calculate optimal start hour
        day_start_hour = self._calculate_day_start_hour(
            current_day_sites,
            site,
            start_location
        )

        # Try to fit site in current day
        fits, _, reason = self.check_site_fits_fn(
            current_day_sites,
            site,
            start_location,
            daily_budget_minutes,
            day_start_hour
        )

        if fits:
            # Site fits, add it
            if self.verbose:
                print(f"  ✓ Site {site_index+1}/{total_sites}: {site.get('site_name')} fits in day {len(days)+1}")
            return {
                'action': 'added',
                'current_day_sites': current_day_sites + [site]
            }

        # Doesn't fit - handle based on reason
        if reason == 'too_late':
            return self._handle_too_late(
                site,
                site_index,
                total_sites,
                current_day_sites,
                days,
                start_location,
                daily_budget_minutes
            )
        else:
            return self._handle_budget_exceeded(
                site,
                site_index,
                total_sites,
                current_day_sites,
                days,
                start_location,
                daily_budget_minutes,
                day_start_hour
            )

    def _calculate_day_start_hour(
        self,
        current_day_sites: List[Dict[str, Any]],
        site: Dict[str, Any],
        start_location: Tuple[float, float]
    ) -> int:
        """Calculate optimal start hour for the day"""
        if not current_day_sites:
            # First site of day
            temp_route = [
                {'lat': start_location[0], 'lon': start_location[1]},
                site
            ]
            return self.calculate_optimal_start_hour_fn(temp_route)
        else:
            # Mid-day - calculate based on first site
            temp_route = [
                {'lat': start_location[0], 'lon': start_location[1]},
                current_day_sites[0]
            ]
            return self.calculate_optimal_start_hour_fn(temp_route)

    def _handle_too_late(
        self,
        site: Dict[str, Any],
        site_index: int,
        total_sites: int,
        current_day_sites: List[Dict[str, Any]],
        days: List[List[Dict[str, Any]]],
        start_location: Tuple[float, float],
        daily_budget_minutes: int
    ) -> Dict[str, Any]:
        """Handle site that arrives too late (roll to next day)"""
        if self.verbose:
            print(f"  ✗ Site {site_index+1}/{total_sites}: {site.get('site_name')} too late for day {len(days)+1}, rolling to next day...")

        # Check if we can start a new day
        if len(days) + 1 >= self.max_trip_minutes / daily_budget_minutes:
            if self.verbose:
                print(f"    ✗ Cannot fit in trip (max days reached), rejecting site")
            return {
                'action': 'rejected',
                'rejected_site': self._create_rejected_site_entry(
                    site,
                    'Could not fit within trip day limits after reordering attempts'
                ),
                'current_day_sites': []
            }

        # Update start location to last site of previous day
        new_start_location = start_location
        if current_day_sites:
            last_site = current_day_sites[-1]
            new_start_location = (last_site['lat'], last_site['lon'])

        # Calculate optimal start for new day
        temp_route = [
            {'lat': new_start_location[0], 'lon': new_start_location[1]},
            site
        ]
        new_day_start_hour = self.calculate_optimal_start_hour_fn(temp_route)

        # Check if site fits in new day
        fits_new_day, _, reason_new_day = self.check_site_fits_fn(
            [],
            site,
            new_start_location,
            daily_budget_minutes,
            new_day_start_hour
        )

        if fits_new_day:
            if self.verbose:
                print(f"    ✓ Started day {len(days)+1} with this site")
            return {
                'action': 'new_day',
                'current_day_sites': [site],
                'start_location': new_start_location
            }
        else:
            if self.verbose:
                print(f"    ✗ Site doesn't fit even in fresh day (reason: {reason_new_day}), rejecting")
            return {
                'action': 'rejected',
                'rejected_site': self._create_rejected_site_entry(
                    site,
                    'Operating hours incompatible with trip schedule'
                ),
                'current_day_sites': []
            }

    def _handle_budget_exceeded(
        self,
        site: Dict[str, Any],
        site_index: int,
        total_sites: int,
        current_day_sites: List[Dict[str, Any]],
        days: List[List[Dict[str, Any]]],
        start_location: Tuple[float, float],
        daily_budget_minutes: int,
        day_start_hour: int
    ) -> Dict[str, Any]:
        """Handle site that doesn't fit due to budget (try reordering)"""
        if self.verbose:
            print(f"  ✗ Site {site_index+1}/{total_sites}: {site.get('site_name')} doesn't fit, trying reorder...")

        # Get adjacent day sites for flexible reordering
        prev_day = days[-1] if days else None
        next_day = None  # We don't have future days built yet

        success, reordered, moved_to_prev, moved_to_next = self.try_reorder_fn(
            current_day_sites,
            site,
            start_location,
            daily_budget_minutes,
            day_start_hour,
            prev_day_sites=prev_day,
            next_day_sites=next_day
        )

        if success:
            # Reordering worked!
            if self.verbose:
                if moved_to_prev and days:
                    print(f"    ✓ Reordering successful, moved {len(moved_to_prev)} site(s) to day {len(days)}")
                print(f"    ✓ Reordering successful, site fits in day {len(days)+1}")

            result = {
                'action': 'reordered',
                'current_day_sites': reordered
            }

            # Update previous day if sites moved there
            if moved_to_prev and days:
                result['update_prev_day'] = True
                result['moved_to_prev'] = moved_to_prev

            return result
        else:
            # Reordering failed - try starting new day
            return self._handle_too_late(
                site,
                site_index,
                total_sites,
                current_day_sites,
                days,
                start_location,
                daily_budget_minutes
            )

    def _create_rejected_site_entry(
        self,
        site: Dict[str, Any],
        reason: str
    ) -> Dict[str, Any]:
        """Create entry for rejected site"""
        return {
            'name': site.get('site_name', 'Unknown'),
            'reason': reason,
            'lat': site.get('lat'),
            'lon': site.get('lon'),
            'operating_hours': site.get('operating_hours', {})
        }

    def _build_resequenced_trip(
        self,
        original_trip: Dict[str, Any],
        days: List[List[Dict[str, Any]]],
        route_details: List[Dict[str, Any]],
        rejected_sites: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Build resequenced trip with updated route details and stats"""
        # Rebuild route_details with resequenced sites
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
            dist = self.haversine_fn(
                stop1['lat'], stop1['lon'],
                stop2['lat'], stop2['lon']
            )
            total_distance += dist
            travel_time = (dist / self.avg_speed_mph) * 60
            visit_time = (
                self.visit_minutes_per_site
                if stop2.get('site_name') != self.home_base.name
                else 0
            )
            total_time += travel_time + visit_time

        resequenced_trip = {
            'trip_number': original_trip['trip_number'],
            'route_details': new_route_details,
            'stats': {
                'total_sites': len(new_route_details) - 2,  # Exclude depot
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
