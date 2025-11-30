"""
Protocols for routing module dependencies.

These protocols enable dependency injection and testing with mocks.
"""
from typing import Protocol, List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class SiteData:
    """Data for a single site (used by protocols)"""
    name: str
    lat: float
    lon: float
    address: str = ""
    city: str = ""
    state: str = ""
    opens_minutes: int = 8 * 60  # 8:00 AM
    closes_minutes: int = 17 * 60  # 5:00 PM
    always_stamp_available: bool = False


class SiteLoader(Protocol):
    """Protocol for loading site data"""

    def load_sites(
        self,
        home_coords: Tuple[float, float],
        max_distance_miles: Optional[float] = None
    ) -> List[SiteData]:
        """
        Load sites, optionally filtered by distance from home.

        Args:
            home_coords: (lat, lon) of home base
            max_distance_miles: Optional max distance filter

        Returns:
            List of SiteData objects
        """
        ...


class DistanceCalculator(Protocol):
    """Protocol for calculating distances between points"""

    def distance_miles(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate distance in miles between two points."""
        ...

    def travel_time_minutes(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float,
        avg_speed_mph: float
    ) -> float:
        """Calculate travel time in minutes between two points."""
        ...


class TimezoneProvider(Protocol):
    """Protocol for looking up timezone from coordinates"""

    def get_timezone(self, lat: float, lon: float) -> str:
        """Get IANA timezone identifier for coordinates."""
        ...


class DistanceMatrix(Protocol):
    """Protocol for distance matrix (can be haversine or from API)"""

    def get(self, from_idx: int, to_idx: int) -> int:
        """Get distance in meters between two node indices."""
        ...


class TimeMatrix(Protocol):
    """Protocol for time matrix (drive + visit time)"""

    def get(self, from_idx: int, to_idx: int) -> int:
        """Get time in minutes between two node indices."""
        ...
