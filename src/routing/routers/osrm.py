"""
OSRM Router

Provides actual road distance and time calculations using Open Source Routing Machine.
Uses the public OSRM demo server by default, with rate limiting.

Rate Limits (demo.project-osrm.org):
- 5000 requests per minute
- 512 requests per persistent connection
- Max 5 seconds between requests on same connection
- Table queries limited to 10,000 elements (origins × destinations)
"""
import requests
from typing import List, Tuple

from .base import (
    Router, RouteResult, DistanceMatrixResult, DistanceSource, HttpClient,
    validate_coordinates, validate_coordinate_list, METERS_PER_MILE, SECONDS_PER_MINUTE
)
from .throttle import RateLimiter


class OSRMError(Exception):
    """Exception raised for OSRM API errors"""
    pass


class OSRMRouter(Router):
    """
    Router using Open Source Routing Machine for actual road routing.

    Provides actual road distances and travel times based on the road network.
    By default uses the public demo server with appropriate rate limiting.

    Rate Limit Compliance:
    - 5000 requests/minute on demo server
    - Automatic throttling when approaching limits
    - Batch requests via table API where possible
    """

    DEFAULT_BASE_URL = "https://router.project-osrm.org"
    DEFAULT_REQUESTS_PER_MINUTE = 5000
    TABLE_MAX_ELEMENTS = 10000  # Max origins × destinations

    def __init__(
        self,
        http_client: HttpClient,
        rate_limiter: RateLimiter,
        base_url: str = None,
        profile: str = "driving"
    ):
        """
        Testing constructor - inject dependencies.

        Args:
            http_client: HTTP client for making requests
            rate_limiter: Rate limiter for throttling
            base_url: OSRM server URL
            profile: Routing profile (driving, walking, cycling)
        """
        self._http_client = http_client
        self._rate_limiter = rate_limiter
        self._base_url = base_url or self.DEFAULT_BASE_URL
        self._profile = profile

    @classmethod
    def create(
        cls,
        base_url: str = None,
        requests_per_minute: int = None,
        profile: str = "driving"
    ) -> "OSRMRouter":  # pragma: no cover
        """
        Default factory - create with real dependencies.

        Args:
            base_url: OSRM server URL (default: public demo server)
            requests_per_minute: Rate limit (default: 5000 for demo server)
            profile: Routing profile (driving, walking, cycling)
        """
        return cls(
            http_client=requests.Session(),
            rate_limiter=RateLimiter(
                requests_per_minute=requests_per_minute or cls.DEFAULT_REQUESTS_PER_MINUTE
            ),
            base_url=base_url,
            profile=profile
        )

    @property
    def name(self) -> str:
        return "OSRM (actual road routing)"

    @property
    def source(self) -> DistanceSource:
        return DistanceSource.OSRM

    @property
    def is_estimated(self) -> bool:
        return False  # Actual road routing

    def _format_coordinates(self, coords: List[Tuple[float, float]]) -> str:
        """Format coordinates for OSRM API (lon,lat;lon,lat format)."""
        return ";".join(f"{lon},{lat}" for lat, lon in coords)

    def _make_request(self, url: str, params: dict = None) -> dict:
        """Make rate-limited request to OSRM API."""
        self._rate_limiter.wait_if_needed()
        self._rate_limiter.record_request()

        try:
            response = self._http_client.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise OSRMError(f"OSRM request failed: {e}") from e

    def get_route(self, origin: Tuple[float, float], destination: Tuple[float, float]) -> RouteResult:
        validate_coordinates(origin[0], origin[1])
        validate_coordinates(destination[0], destination[1])

        coords = self._format_coordinates([origin, destination])
        url = f"{self._base_url}/route/v1/{self._profile}/{coords}"
        params = {"overview": "false"}

        data = self._make_request(url, params)

        if data.get("code") != "Ok":
            raise OSRMError(f"OSRM routing failed: {data.get('message', 'Unknown error')}")

        route = data["routes"][0]
        distance_meters = route["distance"]
        duration_seconds = route["duration"]

        return RouteResult(
            origin=origin,
            destination=destination,
            distance_miles=distance_meters / METERS_PER_MILE,
            duration_minutes=duration_seconds / SECONDS_PER_MINUTE,
            source=DistanceSource.OSRM,
            is_estimated=False
        )

    def get_distance_matrix(
        self,
        origins: List[Tuple[float, float]],
        destinations: List[Tuple[float, float]]
    ) -> DistanceMatrixResult:
        validate_coordinate_list(origins)
        validate_coordinate_list(destinations)

        num_elements = len(origins) * len(destinations)
        if num_elements > self.TABLE_MAX_ELEMENTS:
            raise OSRMError(
                f"Matrix size {num_elements} exceeds OSRM limit of {self.TABLE_MAX_ELEMENTS}. "
                f"Use get_symmetric_matrix_batched() for large matrices."
            )

        all_coords = origins + destinations
        coords_str = self._format_coordinates(all_coords)

        source_indices = list(range(len(origins)))
        dest_indices = list(range(len(origins), len(origins) + len(destinations)))

        url = f"{self._base_url}/table/v1/{self._profile}/{coords_str}"
        params = {
            "sources": ";".join(map(str, source_indices)),
            "destinations": ";".join(map(str, dest_indices)),
            "annotations": "distance,duration"
        }

        data = self._make_request(url, params)

        if data.get("code") != "Ok":
            raise OSRMError(f"OSRM table query failed: {data.get('message', 'Unknown error')}")

        raw_distances = data.get("distances", [])
        raw_durations = data.get("durations", [])

        # Convert: meters to miles, seconds to minutes
        distances = [
            [d / METERS_PER_MILE if d is not None else float('inf') for d in row]
            for row in raw_distances
        ]
        durations = [
            [d / SECONDS_PER_MINUTE if d is not None else float('inf') for d in row]
            for row in raw_durations
        ]

        return DistanceMatrixResult(
            origins=origins,
            destinations=destinations,
            distances=distances,
            durations=durations,
            source=DistanceSource.OSRM,
            is_estimated=False,
            api_calls_made=1
        )

    def get_symmetric_matrix_batched(
        self,
        locations: List[Tuple[float, float]],
        batch_size: int = 100
    ) -> DistanceMatrixResult:
        """
        Calculate symmetric distance matrix with batching for large location sets.
        """
        n = len(locations)

        if n * n <= self.TABLE_MAX_ELEMENTS:
            return self.get_symmetric_matrix(locations)

        distances = [[0.0] * n for _ in range(n)]
        durations = [[0.0] * n for _ in range(n)]
        api_calls = 0

        for i in range(0, n, batch_size):
            batch_origins = locations[i:i + batch_size]
            origin_start = i

            for j in range(0, n, batch_size):
                batch_dests = locations[j:j + batch_size]
                dest_start = j

                result = self.get_distance_matrix(batch_origins, batch_dests)
                api_calls += result.api_calls_made

                for oi, row in enumerate(result.distances):
                    for di, dist in enumerate(row):
                        distances[origin_start + oi][dest_start + di] = dist

                for oi, row in enumerate(result.durations):
                    for di, dur in enumerate(row):
                        durations[origin_start + oi][dest_start + di] = dur

        return DistanceMatrixResult(
            origins=locations,
            destinations=locations,
            distances=distances,
            durations=durations,
            source=DistanceSource.OSRM,
            is_estimated=False,
            api_calls_made=api_calls
        )
