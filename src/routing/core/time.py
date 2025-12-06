#!/usr/bin/env python3
"""
Time calculations for trip planning

Pure functions for computing time matrices and optimal start times
based on distance, travel speed, and site operating hours.
"""
from typing import List, Callable, Dict


def create_time_matrix(
    distance_matrix: List[List[int]],
    avg_speed_mph: float,
    visit_minutes_per_site: int
) -> List[List[int]]:
    """
    Create time matrix in minutes from distance matrix.

    Includes both driving time and site visit time.

    Args:
        distance_matrix: NxN matrix of distances in meters
        avg_speed_mph: Average driving speed in miles per hour
        visit_minutes_per_site: Time to spend at each site (minutes)

    Returns:
        NxN matrix where matrix[i][j] is total time from i to j (drive + visit)
        Note: depot (index 0) has no visit time

    Examples:
        >>> # 2 sites: depot and one site 55 miles away
        >>> dist_matrix = [[0, 88514], [88514, 0]]  # ~55 miles in meters
        >>> time_matrix = create_time_matrix(dist_matrix, 55.0, 240)
        >>> # Drive time: 55 miles / 55 mph = 60 min, visit time: 240 min
        >>> time_matrix[0][1]  # depot to site 1
        300
        >>> time_matrix[1][0]  # site 1 to depot (no visit time at depot)
        60
    """
    n = len(distance_matrix)
    matrix = [[0] * n for _ in range(n)]

    for i in range(n):
        for j in range(n):
            if i != j:
                # Convert meters to miles and calculate drive time
                dist_miles = distance_matrix[i][j] / 1609.34
                drive_minutes = int((dist_miles / avg_speed_mph) * 60)

                # Add visit time (but not at depot, which is index 0)
                visit_minutes = 0 if j == 0 else visit_minutes_per_site
                matrix[i][j] = drive_minutes + visit_minutes

    return matrix


def calculate_optimal_start_hour(
    route_details: List[Dict],
    haversine_distance: Callable[[float, float, float, float], float],
    avg_speed_mph: float,
    preferred_start_hour: int = 9,
    earliest_start_hour: int = 6
) -> int:
    """
    Calculate optimal trip start time based on first site operating hours.

    Strategy:
    - Calculate travel time from depot to first site
    - Set start time so we arrive exactly when first site opens
    - Prefer starting at preferred_start_hour (9am) if that works
    - Never start before earliest_start_hour (6am)

    Args:
        route_details: List of sites in order (first entry is depot)
        haversine_distance: Function to calculate distance between two points
        avg_speed_mph: Average driving speed
        preferred_start_hour: Preferred start time (default 9am)
        earliest_start_hour: Earliest allowed start (default 6am)

    Returns:
        Optimal start hour (6-21)

    Examples:
        >>> from core.distance import haversine_distance
        >>> route = [
        ...     {'lat': 38.5831, 'lon': -90.4068},  # Depot
        ...     {'lat': 38.6247, 'lon': -90.1848,  # Site opens at 8am
        ...      'operating_hours': {'opens': 8 * 60}}
        ... ]
        >>> start = calculate_optimal_start_hour(route, haversine_distance, 55.0)
        >>> 6 <= start <= 9
        True
    """
    if len(route_details) < 2:  # Only depot, no sites
        return preferred_start_hour

    depot = route_details[0]
    first_site = route_details[1]

    # Calculate actual travel time from depot to first site
    travel_distance_miles = haversine_distance(
        depot['lat'], depot['lon'],
        first_site['lat'], first_site['lon']
    )
    travel_time_minutes = (travel_distance_miles / avg_speed_mph) * 60

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
        if required_start_hour < earliest_start_hour:
            # Starting before 6 AM would be needed to arrive at opening
            # Check if starting at 6 AM would arrive before opening
            arrival_at_earliest = earliest_start_hour * 60 + travel_time_minutes

            if arrival_at_earliest < opens_minutes:
                # Starting at 6 AM arrives before opening
                # Calculate latest start to arrive at opening (with small buffer)
                # Allow arriving up to 30 min early as acceptable
                target_arrival = opens_minutes - 30  # 30 min early buffer
                optimal_start_minutes = target_arrival - travel_time_minutes
                optimal_start_hour = optimal_start_minutes / 60.0

                # Use the later of: earliest allowed (6am) or optimal
                return max(earliest_start_hour, int(optimal_start_hour))
            else:
                # Starting at 6 AM arrives at or after opening - acceptable
                return earliest_start_hour
        elif required_start_hour <= preferred_start_hour:
            # Need to start before or at 9am to arrive at opening time
            # Round to nearest hour (not down) for better arrival timing
            return round(required_start_hour)
        else:
            # Opening time is late enough that we can start at preferred time
            # and still arrive after/when it opens
            return preferred_start_hour

    # No operating hours - use preferred start time
    return preferred_start_hour


if __name__ == '__main__':
    # Quick validation
    print("Testing create_time_matrix...")

    # Test 1: Basic time matrix calculation
    # 2 locations: depot and site 55 miles away (88514 meters)
    distance_matrix = [[0, 88514], [88514, 0]]
    time_matrix = create_time_matrix(distance_matrix, 55.0, 240)

    # Drive time: 55 miles / 55 mph = 60 min
    # depot -> site: 60 min drive + 240 min visit = 300 min
    assert time_matrix[0][1] == 300, f"Expected 300, got {time_matrix[0][1]}"
    print(f"  ✓ depot -> site: {time_matrix[0][1]} min")

    # site -> depot: 60 min drive + 0 min visit = 60 min
    assert time_matrix[1][0] == 60, f"Expected 60, got {time_matrix[1][0]}"
    print(f"  ✓ site -> depot: {time_matrix[1][0]} min")

    # Test 2: Diagonal should be zero
    assert time_matrix[0][0] == 0
    assert time_matrix[1][1] == 0
    print("  ✓ Diagonal is zero")

    print("✓ Time matrix calculation validated")

    print("\nTesting calculate_optimal_start_hour...")

    # Need to import haversine for testing
    import sys
    sys.path.insert(0, '/workspace/src/routing')
    from core.distance import haversine_distance

    # Test 1: No sites (only depot)
    route = [{'lat': 38.5831, 'lon': -90.4068}]
    start = calculate_optimal_start_hour(route, haversine_distance, 55.0)
    assert start == 9, f"Expected 9, got {start}"
    print(f"  ✓ No sites returns preferred start: {start}")

    # Test 2: Site with early opening (8am)
    route = [
        {'lat': 38.5831, 'lon': -90.4068},  # Depot
        {'lat': 38.6247, 'lon': -90.1848, 'operating_hours': {'opens': 8 * 60}}
    ]
    start = calculate_optimal_start_hour(route, haversine_distance, 55.0)
    assert 6 <= start <= 9, f"Expected 6-9, got {start}"
    print(f"  ✓ Early opening site: {start}")

    # Test 3: Site with late opening (11am)
    route = [
        {'lat': 38.5831, 'lon': -90.4068},  # Depot
        {'lat': 38.6247, 'lon': -90.1848, 'operating_hours': {'opens': 11 * 60}}
    ]
    start = calculate_optimal_start_hour(route, haversine_distance, 55.0)
    assert start == 9, f"Expected 9, got {start}"
    print(f"  ✓ Late opening site returns preferred: {start}")

    print("✓ Optimal start hour calculation validated")
