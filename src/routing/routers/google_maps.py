"""
Google Maps Router

Provides actual road distance and time calculations using Google Maps Distance Matrix API.

Rate Limits:
- 60,000 elements per minute (origins × destinations per request)
- Maximum 25 origins OR 25 destinations per request
- Maximum 100 elements per request (origins × destinations)
- Pay-as-you-go pricing (~$5-10 per 1000 requests)
- $200/month free credit

Requires GOOGLE_MAPS_API_KEY environment variable.
"""
import os
import requests
from typing import List, Tuple

from .base import (
    Router, RouteResult, DistanceMatrixResult, DistanceSource, HttpClient,
    validate_coordinates, validate_coordinate_list, METERS_PER_MILE, SECONDS_PER_MINUTE
)
from .throttle import ElementRateLimiter


class GoogleMapsError(Exception):
    """Exception raised for Google Maps API errors"""
    pass


class GoogleMapsRouter(Router):
    """
    Router using Google Maps Distance Matrix API for actual road routing.

    Provides actual road distances and travel times with traffic consideration.
    Requires a valid Google Maps API key.

    Rate Limit Compliance:
    - 60,000 elements/minute
    - 25 destinations per request maximum
    - Automatic batching for large requests
    """

    BASE_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"
    DEFAULT_ELEMENTS_PER_MINUTE = 60000
    MAX_DESTINATIONS_PER_REQUEST = 25
    MAX_ELEMENTS_PER_REQUEST = 100

    def __init__(
        self,
        http_client: HttpClient,
        rate_limiter: ElementRateLimiter,
        api_key: str,
    ):
        """
        Testing constructor - inject dependencies.

        Args:
            http_client: HTTP client for making requests
            rate_limiter: Element rate limiter for throttling
            api_key: Google Maps API key
        """
        self._http_client = http_client
        self._rate_limiter = rate_limiter
        self._api_key = api_key

    @classmethod
    def create(
        cls,
        api_key: str = None,
        elements_per_minute: int = None
    ) -> "GoogleMapsRouter":  # pragma: no cover
        """
        Default factory - create with real dependencies.

        Args:
            api_key: Google Maps API key (default: from GOOGLE_MAPS_API_KEY env var)
            elements_per_minute: Rate limit (default: 60000)
        """
        resolved_key = api_key or os.environ.get("GOOGLE_MAPS_API_KEY")
        if not resolved_key:
            raise GoogleMapsError(
                "Google Maps API key required. Set GOOGLE_MAPS_API_KEY environment variable "
                "or pass api_key parameter."
            )

        return cls(
            http_client=requests.Session(),
            rate_limiter=ElementRateLimiter(
                elements_per_minute=elements_per_minute or cls.DEFAULT_ELEMENTS_PER_MINUTE
            ),
            api_key=resolved_key
        )

    @property
    def name(self) -> str:
        return "Google Maps (actual road routing)"

    @property
    def source(self) -> DistanceSource:
        return DistanceSource.GOOGLE_MAPS

    @property
    def is_estimated(self) -> bool:
        return False  # Actual road routing

    def _format_locations(self, coords: List[Tuple[float, float]]) -> str:
        """Format coordinates for Google Maps API (lat,lng|lat,lng format)."""
        return "|".join(f"{lat},{lon}" for lat, lon in coords)

    def _make_request(self, origins: List[Tuple[float, float]], destinations: List[Tuple[float, float]]) -> dict:
        """Make rate-limited request to Google Maps API."""
        element_count = len(origins) * len(destinations)
        self._rate_limiter.wait_if_needed(element_count)
        self._rate_limiter.record_elements(element_count)

        params = {
            "origins": self._format_locations(origins),
            "destinations": self._format_locations(destinations),
            "key": self._api_key,
            "units": "imperial"  # Get distances in miles
        }

        try:
            response = self._http_client.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise GoogleMapsError(f"Google Maps request failed: {e}") from e

    def get_route(self, origin: Tuple[float, float], destination: Tuple[float, float]) -> RouteResult:
        validate_coordinates(origin[0], origin[1])
        validate_coordinates(destination[0], destination[1])

        data = self._make_request([origin], [destination])

        if data.get("status") != "OK":
            raise GoogleMapsError(f"Google Maps API error: {data.get('status')} - {data.get('error_message', '')}")

        element = data["rows"][0]["elements"][0]
        if element.get("status") != "OK":
            raise GoogleMapsError(f"Route not found: {element.get('status')}")

        # Distance comes in meters when units=imperial (text is in miles)
        distance_meters = element["distance"]["value"]
        duration_seconds = element["duration"]["value"]

        return RouteResult(
            origin=origin,
            destination=destination,
            distance_miles=distance_meters / METERS_PER_MILE,
            duration_minutes=duration_seconds / SECONDS_PER_MINUTE,
            source=DistanceSource.GOOGLE_MAPS,
            is_estimated=False
        )

    def get_distance_matrix(
        self,
        origins: List[Tuple[float, float]],
        destinations: List[Tuple[float, float]]
    ) -> DistanceMatrixResult:
        """
        Calculate distance matrix, batching if necessary.

        Google Maps limits:
        - 25 destinations per request
        - 100 elements per request
        """
        validate_coordinate_list(origins)
        validate_coordinate_list(destinations)

        num_origins = len(origins)
        num_destinations = len(destinations)

        # Initialize result matrices
        distances: List[List[float]] = [[0.0] * num_destinations for _ in range(num_origins)]
        durations: List[List[float]] = [[0.0] * num_destinations for _ in range(num_origins)]
        api_calls = 0

        # Batch by destination chunks (max 25 per request)
        dest_batch_size = min(self.MAX_DESTINATIONS_PER_REQUEST, self.MAX_ELEMENTS_PER_REQUEST // max(1, num_origins))

        for dest_start in range(0, num_destinations, dest_batch_size):
            dest_end = min(dest_start + dest_batch_size, num_destinations)
            dest_batch = destinations[dest_start:dest_end]

            # Further batch origins if needed to stay under 100 elements
            origin_batch_size = self.MAX_ELEMENTS_PER_REQUEST // len(dest_batch)

            for origin_start in range(0, num_origins, origin_batch_size):
                origin_end = min(origin_start + origin_batch_size, num_origins)
                origin_batch = origins[origin_start:origin_end]

                data = self._make_request(origin_batch, dest_batch)
                api_calls += 1

                if data.get("status") != "OK":
                    raise GoogleMapsError(f"Google Maps API error: {data.get('status')}")

                # Parse results into matrices
                for oi, row in enumerate(data["rows"]):
                    for di, element in enumerate(row["elements"]):
                        if element.get("status") == "OK":
                            dist_meters = element["distance"]["value"]
                            dur_seconds = element["duration"]["value"]
                            distances[origin_start + oi][dest_start + di] = dist_meters / METERS_PER_MILE
                            durations[origin_start + oi][dest_start + di] = dur_seconds / SECONDS_PER_MINUTE
                        else:
                            # Route not found
                            distances[origin_start + oi][dest_start + di] = float('inf')
                            durations[origin_start + oi][dest_start + di] = float('inf')

        return DistanceMatrixResult(
            origins=origins,
            destinations=destinations,
            distances=distances,
            durations=durations,
            source=DistanceSource.GOOGLE_MAPS,
            is_estimated=False,
            api_calls_made=api_calls
        )
