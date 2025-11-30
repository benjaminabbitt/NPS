"""
Base Router Interface

Defines the abstract interface for all routing backends.
All routers must implement distance/time calculation with source tracking.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional, Protocol, Dict, Any

# Conversion constants
METERS_PER_MILE = 1609.34
SECONDS_PER_MINUTE = 60.0


def validate_coordinates(lat: float, lon: float) -> None:
    """
    Validate that coordinates are within valid ranges.

    Args:
        lat: Latitude (-90 to 90)
        lon: Longitude (-180 to 180)

    Raises:
        ValueError: If coordinates are out of range
    """
    if not (-90 <= lat <= 90):
        raise ValueError(f"Invalid latitude {lat}: must be between -90 and 90")
    if not (-180 <= lon <= 180):
        raise ValueError(f"Invalid longitude {lon}: must be between -180 and 180")


def validate_coordinate_list(coords: List[Tuple[float, float]]) -> None:
    """Validate a list of (lat, lon) coordinate tuples."""
    if not coords:
        raise ValueError("Coordinate list cannot be empty")
    for lat, lon in coords:
        validate_coordinates(lat, lon)


class HttpResponse(Protocol):
    """Protocol for HTTP response - allows injection for testing."""

    def raise_for_status(self) -> None:
        """Raise exception if status code indicates error."""
        ...

    def json(self) -> dict:
        """Parse response body as JSON."""
        ...


class HttpClient(Protocol):
    """Protocol for HTTP client - allows injection for testing."""

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: int = 30
    ) -> HttpResponse:
        """Make GET request with optional params and return response."""
        ...


class DistanceSource(Enum):
    """Source of distance/time data - tracks whether values are estimated or actual"""
    HAVERSINE = "haversine"  # Straight-line distance, time derived from speed
    OSRM = "osrm"            # Open Source Routing Machine (actual road distance/time)
    GOOGLE_MAPS = "google"   # Google Maps Distance Matrix API
    CACHE = "cache"          # Retrieved from cache


@dataclass
class RouteResult:
    """Result from a single route calculation"""
    origin: Tuple[float, float]       # (lat, lon)
    destination: Tuple[float, float]  # (lat, lon)
    distance_miles: float
    duration_minutes: float
    source: DistanceSource
    is_estimated: bool  # True if derived from straight-line distance

    @property
    def duration_hours(self) -> float:
        return self.duration_minutes / 60.0


@dataclass
class DistanceMatrixResult:
    """Result from a distance matrix calculation"""
    origins: List[Tuple[float, float]]
    destinations: List[Tuple[float, float]]
    distances: List[List[float]]  # [origin_idx][dest_idx] in miles
    durations: List[List[float]]  # [origin_idx][dest_idx] in minutes
    source: DistanceSource
    is_estimated: bool
    api_calls_made: int = 0

    def get_distance(self, origin_idx: int, dest_idx: int) -> float:
        return self.distances[origin_idx][dest_idx]

    def get_duration(self, origin_idx: int, dest_idx: int) -> float:
        return self.durations[origin_idx][dest_idx]


class Router(ABC):
    """Abstract base class for routing providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this router"""
        pass

    @property
    @abstractmethod
    def source(self) -> DistanceSource:
        """The DistanceSource enum value for this router"""
        pass

    @property
    @abstractmethod
    def is_estimated(self) -> bool:
        """Whether this router provides estimates (True) or actual routing data (False)"""
        pass

    @abstractmethod
    def get_route(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float]
    ) -> RouteResult:
        """Calculate route between two points."""
        pass

    @abstractmethod
    def get_distance_matrix(
        self,
        origins: List[Tuple[float, float]],
        destinations: List[Tuple[float, float]]
    ) -> DistanceMatrixResult:
        """Calculate distances between all origin-destination pairs."""
        pass

    def get_symmetric_matrix(
        self,
        locations: List[Tuple[float, float]]
    ) -> DistanceMatrixResult:
        """Calculate symmetric distance matrix for VRP problems."""
        return self.get_distance_matrix(locations, locations)
