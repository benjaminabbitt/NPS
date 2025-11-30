"""
Geographic utilities for routing calculations.

Provides haversine distance calculation and coordinate validation.
"""
import math
from typing import Tuple, List

# Earth's radius in miles
EARTH_RADIUS_MILES = 3959


def haversine_distance(
    lat1: float, lon1: float,
    lat2: float, lon2: float
) -> float:
    """
    Calculate great-circle distance between two points using haversine formula.

    Args:
        lat1, lon1: First point coordinates (latitude, longitude in degrees)
        lat2, lon2: Second point coordinates (latitude, longitude in degrees)

    Returns:
        Distance in miles

    Raises:
        ValueError: If coordinates are out of valid range
    """
    # Validate coordinates
    _validate_lat_lon(lat1, lon1)
    _validate_lat_lon(lat2, lon2)

    # Handle same location
    if lat1 == lat2 and lon1 == lon2:
        return 0.0

    # Convert to radians
    lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(
        math.radians, [lat1, lon1, lat2, lon2]
    )

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)

    return EARTH_RADIUS_MILES * 2 * math.asin(math.sqrt(a))


def _validate_lat_lon(lat: float, lon: float) -> None:
    """Validate latitude and longitude are in valid ranges."""
    if not (-90 <= lat <= 90):
        raise ValueError(f"Invalid latitude {lat}: must be between -90 and 90")
    if not (-180 <= lon <= 180):
        raise ValueError(f"Invalid longitude {lon}: must be between -180 and 180")


def travel_time_minutes(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
    avg_speed_mph: float = 55.0
) -> float:
    """
    Calculate estimated travel time between two points.

    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates
        avg_speed_mph: Average driving speed in mph (default: 55)

    Returns:
        Estimated travel time in minutes
    """
    if avg_speed_mph <= 0:
        raise ValueError("avg_speed_mph must be positive")

    distance = haversine_distance(lat1, lon1, lat2, lon2)
    return (distance / avg_speed_mph) * 60.0


def distance_matrix(
    locations: List[Tuple[float, float]],
    in_meters: bool = False
) -> List[List[float]]:
    """
    Calculate symmetric distance matrix for a list of locations.

    Args:
        locations: List of (lat, lon) tuples
        in_meters: If True, return distances in meters; otherwise miles

    Returns:
        2D matrix where matrix[i][j] is distance from location i to j
    """
    n = len(locations)
    matrix = [[0.0] * n for _ in range(n)]

    meters_per_mile = 1609.34

    for i in range(n):
        for j in range(i + 1, n):
            dist = haversine_distance(
                locations[i][0], locations[i][1],
                locations[j][0], locations[j][1]
            )
            if in_meters:
                dist *= meters_per_mile

            matrix[i][j] = dist
            matrix[j][i] = dist  # Symmetric

    return matrix
