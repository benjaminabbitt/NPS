#!/usr/bin/env python3
"""
Distance calculations for trip planning

Pure functions for calculating distances between geographic coordinates
using the Haversine formula.
"""
import math
from typing import List


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two points on Earth.

    Uses the Haversine formula to compute the shortest distance over
    the earth's surface, giving an "as-the-crow-flies" distance.

    Args:
        lat1: Latitude of first point (degrees)
        lon1: Longitude of first point (degrees)
        lat2: Latitude of second point (degrees)
        lon2: Longitude of second point (degrees)

    Returns:
        Distance in miles

    Examples:
        >>> # Kirkwood, MO to St. Louis Arch (~10 miles)
        >>> d = haversine_distance(38.5831, -90.4068, 38.6247, -90.1848)
        >>> 9 < d < 13
        True

        >>> # Same point
        >>> haversine_distance(38.5831, -90.4068, 38.5831, -90.4068)
        0.0
    """
    R = 3959  # Earth radius in miles
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def create_distance_matrix(sites: List[tuple]) -> List[List[int]]:
    """
    Create distance matrix in meters for all site pairs.

    Args:
        sites: List of (lat, lon) tuples for each site

    Returns:
        NxN matrix where matrix[i][j] is distance from site i to j in meters

    Examples:
        >>> sites = [(38.5831, -90.4068), (38.6247, -90.1848)]
        >>> matrix = create_distance_matrix(sites)
        >>> matrix[0][0]  # Distance to self
        0
        >>> matrix[0][1] == matrix[1][0]  # Symmetric
        True
        >>> matrix[0][1] > 0  # Positive distance
        True
    """
    n = len(sites)
    matrix = [[0] * n for _ in range(n)]

    for i in range(n):
        for j in range(n):
            if i != j:
                lat1, lon1 = sites[i]
                lat2, lon2 = sites[j]
                dist_miles = haversine_distance(lat1, lon1, lat2, lon2)
                matrix[i][j] = int(dist_miles * 1609.34)  # Convert to meters

    return matrix


if __name__ == '__main__':
    # Quick validation
    print("Testing haversine_distance...")

    # Test 1: Same point
    d = haversine_distance(38.5831, -90.4068, 38.5831, -90.4068)
    assert d == 0.0, f"Same point should be 0, got {d}"

    # Test 2: Kirkwood to St. Louis Arch
    d = haversine_distance(38.5831, -90.4068, 38.6247, -90.1848)
    assert 9 < d < 13, f"Kirkwood to STL should be ~10mi, got {d}"

    # Test 3: LA to SF
    d = haversine_distance(34.0522, -118.2437, 37.7749, -122.4194)
    assert 330 < d < 360, f"LA to SF should be ~340mi, got {d}"

    print("✓ All distance calculations validated")

    print("\nTesting create_distance_matrix...")
    sites = [(38.5831, -90.4068), (38.6247, -90.1848), (38.6270, -90.1994)]
    matrix = create_distance_matrix(sites)

    # Diagonal should be zero
    for i in range(len(matrix)):
        assert matrix[i][i] == 0, f"Diagonal {i} should be 0"

    # Should be symmetric
    for i in range(len(matrix)):
        for j in range(len(matrix)):
            assert matrix[i][j] == matrix[j][i], f"Matrix not symmetric at ({i},{j})"

    print("✓ Distance matrix validated")
