"""
Haversine Router

Provides distance calculations using straight-line (great circle) distance.
Time is ESTIMATED from distance using a configurable average speed.

This is the fastest router but provides estimates, not actual road distances.
All times returned are distance-derived estimates.
"""
import math
from typing import List, Tuple

from .base import Router, RouteResult, DistanceMatrixResult, DistanceSource


class HaversineRouter(Router):
    """
    Router using Haversine formula for straight-line distances.

    Times are ESTIMATED by dividing distance by average speed.
    Does not account for road network, speed limits, or traffic.
    """

    EARTH_RADIUS_MILES = 3959

    def __init__(self, avg_speed_mph: float = 55.0):
        self._avg_speed_mph = avg_speed_mph

    @property
    def name(self) -> str:
        return f"Haversine (estimated @ {self._avg_speed_mph} mph)"

    @property
    def source(self) -> DistanceSource:
        return DistanceSource.HAVERSINE

    @property
    def is_estimated(self) -> bool:
        return True

    @property
    def avg_speed_mph(self) -> float:
        return self._avg_speed_mph

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate great-circle distance in miles."""
        lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
        lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        return self.EARTH_RADIUS_MILES * 2 * math.asin(math.sqrt(a))

    def _estimate_duration(self, distance_miles: float) -> float:
        """Estimate travel duration in minutes (distance-derived)."""
        if distance_miles == 0:
            return 0.0
        return (distance_miles / self._avg_speed_mph) * 60.0

    def get_route(self, origin: Tuple[float, float], destination: Tuple[float, float]) -> RouteResult:
        lat1, lon1 = origin
        lat2, lon2 = destination

        distance = self._haversine_distance(lat1, lon1, lat2, lon2)
        duration = self._estimate_duration(distance)

        return RouteResult(
            origin=origin,
            destination=destination,
            distance_miles=distance,
            duration_minutes=duration,
            source=DistanceSource.HAVERSINE,
            is_estimated=True
        )

    def get_distance_matrix(
        self,
        origins: List[Tuple[float, float]],
        destinations: List[Tuple[float, float]]
    ) -> DistanceMatrixResult:
        num_origins = len(origins)
        num_destinations = len(destinations)

        distances: List[List[float]] = [[0.0] * num_destinations for _ in range(num_origins)]
        durations: List[List[float]] = [[0.0] * num_destinations for _ in range(num_origins)]

        for i, (lat1, lon1) in enumerate(origins):
            for j, (lat2, lon2) in enumerate(destinations):
                dist = self._haversine_distance(lat1, lon1, lat2, lon2)
                distances[i][j] = dist
                durations[i][j] = self._estimate_duration(dist)

        return DistanceMatrixResult(
            origins=origins,
            destinations=destinations,
            distances=distances,
            durations=durations,
            source=DistanceSource.HAVERSINE,
            is_estimated=True,
            api_calls_made=0
        )
