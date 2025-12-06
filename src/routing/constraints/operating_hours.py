#!/usr/bin/env python3
"""
Operating hours constraints for trip planning

Functions for validating site visits against operating hours
and checking if sites fit within day budgets.
"""
from typing import List, Dict, Tuple, Callable


def parse_time_string(time_str: str, default_minutes: int) -> int:
    """
    Parse time string in HH:MM format to minutes since midnight.

    Args:
        time_str: Time string (e.g., "09:00", "9:00", or integer minutes)
        default_minutes: Default value if parsing fails

    Returns:
        Minutes since midnight (0-1439)

    Examples:
        >>> parse_time_string("09:00", 540)
        540
        >>> parse_time_string("17:30", 540)
        1050
        >>> parse_time_string(540, 540)
        540
    """
    if isinstance(time_str, int):
        return time_str

    if isinstance(time_str, str) and ':' in time_str:
        parts = time_str.split(':')
        return int(parts[0]) * 60 + int(parts[1])

    return default_minutes


def check_site_fits_in_day(
    sites_in_day: List[Dict],
    new_site: Dict,
    start_location: Tuple[float, float],
    day_budget_minutes: int,
    start_hour: int,
    haversine_distance: Callable[[float, float, float, float], float],
    avg_speed_mph: float,
    visit_minutes_per_site: int
) -> Tuple[bool, float, str]:
    """
    Check if adding new_site to sites_in_day fits within day budget and operating hours.

    Args:
        sites_in_day: List of site dicts already in the day
        new_site: Site dict to try adding
        start_location: (lat, lon) tuple of where the day starts
        day_budget_minutes: Total minutes available in the day
        start_hour: Hour when day starts (e.g., 6 or 9)
        haversine_distance: Function to calculate distance between two points
        avg_speed_mph: Average driving speed
        visit_minutes_per_site: Time to spend at each site

    Returns:
        (fits, arrival_time_minutes, reason) - tuple with:
            fits: True if site fits in this day
            arrival_time_minutes: arrival time from start of day
            reason: 'ok', 'budget_exceeded', 'too_early', 'too_late'

    Examples:
        >>> from core.distance import haversine_distance
        >>> sites = []
        >>> new = {'lat': 38.6247, 'lon': -90.1848}
        >>> start = (38.5831, -90.4068)
        >>> fits, arrival, reason = check_site_fits_in_day(
        ...     sites, new, start, 900, 9, haversine_distance, 55.0, 240
        ... )
        >>> fits
        True
        >>> reason
        'ok'
    """
    # Calculate cumulative time to reach new site
    current_time = 0
    current_location = start_location

    # Account for travel and visit time for all sites already in day
    for site in sites_in_day:
        travel_dist = haversine_distance(
            current_location[0], current_location[1],
            site['lat'], site['lon']
        )
        travel_time = (travel_dist / avg_speed_mph) * 60
        visit_time = visit_minutes_per_site
        current_time += travel_time + visit_time
        current_location = (site['lat'], site['lon'])

    # Now calculate time to reach new site
    travel_dist = haversine_distance(
        current_location[0], current_location[1],
        new_site['lat'], new_site['lon']
    )
    travel_time = (travel_dist / avg_speed_mph) * 60
    arrival_time = current_time + travel_time

    # Check if arrival + visit fits in day budget
    if arrival_time + visit_minutes_per_site > day_budget_minutes:
        return False, arrival_time, 'budget_exceeded'

    # Check operating hours if site has them
    if 'operating_hours' in new_site and new_site['operating_hours']:
        op_hours = new_site['operating_hours']

        # Skip if stamps always available
        if new_site.get('always_stamp_available', False):
            return True, arrival_time, 'ok'

        # Calculate wall-clock arrival time
        arrival_minutes_of_day = (start_hour * 60) + arrival_time
        arrival_hour = (arrival_minutes_of_day // 60) % 24
        arrival_minute = arrival_minutes_of_day % 60

        # Parse operating hours
        opens_str = op_hours.get('opens', '09:00')
        closes_str = op_hours.get('closes', '17:00')

        opens_minutes = parse_time_string(opens_str, 9 * 60)
        closes_minutes = parse_time_string(closes_str, 17 * 60)

        # Check if arrival is within operating hours
        arrival_minutes_total = arrival_hour * 60 + arrival_minute

        # Allow early arrivals (before visitor center opens) - user can wait
        # Only reject if too late (after closing)
        if arrival_minutes_total > closes_minutes:
            return False, arrival_time, 'too_late'

    return True, arrival_time, 'ok'


if __name__ == '__main__':
    # Quick validation
    print("Testing parse_time_string...")

    # Test 1: String format
    assert parse_time_string("09:00", 540) == 540
    print("  ✓ Parse '09:00' = 540")

    assert parse_time_string("17:30", 540) == 1050
    print("  ✓ Parse '17:30' = 1050")

    # Test 2: Integer passthrough
    assert parse_time_string(540, 0) == 540
    print("  ✓ Integer passthrough")

    # Test 3: Invalid string returns default
    assert parse_time_string("invalid", 600) == 600
    print("  ✓ Invalid string returns default")

    print("✓ parse_time_string validated")

    print("\nTesting check_site_fits_in_day...")

    # Need imports for testing
    import sys
    sys.path.insert(0, '/workspace/src/routing')
    from core.distance import haversine_distance

    # Test 1: Empty day, site fits
    sites = []
    new_site = {'lat': 38.6247, 'lon': -90.1848}
    start = (38.5831, -90.4068)
    fits, arrival, reason = check_site_fits_in_day(
        sites, new_site, start, 900, 9, haversine_distance, 55.0, 240
    )
    assert fits is True
    assert reason == 'ok'
    print(f"  ✓ Empty day, site fits: arrival={arrival:.1f}min")

    # Test 2: Budget exceeded
    sites = []
    new_site = {'lat': 38.6247, 'lon': -90.1848}
    start = (38.5831, -90.4068)
    fits, arrival, reason = check_site_fits_in_day(
        sites, new_site, start, 100, 9, haversine_distance, 55.0, 240
    )
    assert fits is False
    assert reason == 'budget_exceeded'
    print(f"  ✓ Budget exceeded: reason={reason}")

    # Test 3: Operating hours - too late
    sites = []
    new_site = {
        'lat': 38.6247,
        'lon': -90.1848,
        'operating_hours': {'opens': '08:00', 'closes': '17:00'}
    }
    start = (38.5831, -90.4068)
    # Start at 5pm (17:00), will arrive after closing
    fits, arrival, reason = check_site_fits_in_day(
        sites, new_site, start, 900, 17, haversine_distance, 55.0, 240
    )
    assert fits is False
    assert reason == 'too_late'
    print(f"  ✓ Operating hours violation: reason={reason}")

    # Test 4: Always stamp available ignores hours
    sites = []
    new_site = {
        'lat': 38.6247,
        'lon': -90.1848,
        'operating_hours': {'opens': '08:00', 'closes': '17:00'},
        'always_stamp_available': True
    }
    start = (38.5831, -90.4068)
    fits, arrival, reason = check_site_fits_in_day(
        sites, new_site, start, 900, 17, haversine_distance, 55.0, 240
    )
    assert fits is True
    assert reason == 'ok'
    print(f"  ✓ Always stamp available ignores hours: reason={reason}")

    print("✓ check_site_fits_in_day validated")
