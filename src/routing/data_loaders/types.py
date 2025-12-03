#!/usr/bin/env python3
"""
Common types and protocols for data loaders
"""
from typing import Protocol, Dict, Any, List, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class CancellationStamp:
    """Cancellation stamp location with completion tracking"""
    location: str
    address: str
    hours: str = ""
    phone: str = ""
    geocode: Optional[Tuple[float, float]] = None
    completed: bool = False


@dataclass
class Activity:
    """Activity with details and completion tracking"""
    name: str
    duration_hours: float = 0.0
    description: str = ""
    address: str = ""
    hours: str = ""
    distance: str = ""  # For "Also Nearby" items
    sources: List[str] = field(default_factory=list)
    completed: bool = False


@dataclass
class OperatingHours:
    """Operating hours for a site (compatible with VRP solver)"""
    opens: int  # Minutes since midnight (e.g., 540 for 9:00 AM)
    closes: int  # Minutes since midnight (e.g., 1020 for 5:00 PM)


@dataclass
class WorldsLargestAttraction:
    """World's Largest tourist attraction"""
    name: str
    title: str  # "World's Longest Cave System"
    what_makes_it_largest: str
    address: str
    geocode: Optional[Tuple[float, float]] = None
    hours: str = ""
    fees: str = ""
    history: str = ""
    seasonal_info: str = ""
    verification: str = ""  # ✓, [SELF-DECLARED], [CONTESTED], etc.
    source: str = ""
    category: str = ""  # Natural Formations, Buildings, etc.
    completed: bool = False  # User tracking


@dataclass
class CoasterRide:
    """Individual coaster ride tracking"""
    name: str
    park_name: str
    rank: str = ""
    manufacturer: str = ""
    rating: str = ""
    height_requirement: str = ""
    roughness: str = ""
    memorable_moments: List[str] = field(default_factory=list)
    reviews: str = ""

    # Tracking per person
    ridden_honor: bool = False
    ridden_ben: bool = False
    ridden_amber: bool = False
    notes: str = ""  # Freeform notes

    file_path: Optional[Path] = None


class FileReader(Protocol):
    """Protocol for reading files"""

    def read(self, file_path: Path) -> str:
        """Read file contents as string"""
        ...


class FrontmatterParser(Protocol):
    """Protocol for parsing frontmatter from markdown"""

    def parse(self, content: str) -> Tuple[Dict[str, Any], str]:
        """
        Parse frontmatter and content from markdown string.

        Returns:
            (metadata_dict, content_string)
        """
        ...


class MarkdownParser(Protocol):
    """Protocol for parsing markdown content into structured data"""

    def parse(self, content: str) -> Dict[str, List[str]]:
        """
        Parse markdown content into sections with list items.

        Returns:
            Dictionary mapping section titles to list of items
        """
        ...


class DurationParser(Protocol):
    """Protocol for parsing duration strings to hours"""

    def parse(self, duration_str: str) -> float:
        """
        Parse duration string to hours.

        Examples:
            "4 hours" -> 4.0
            "2-3 hours" -> 2.5
            "30 minutes" -> 0.5
        """
        ...


class OperatingHoursParser(Protocol):
    """Protocol for parsing operating hours strings"""

    def parse(self, hours_str: str) -> Optional[OperatingHours]:
        """
        Parse hours string to OperatingHours.

        Examples:
            "9:00 AM - 5:00 PM" -> OperatingHours(540, 1020)
            "Daily 8:00 AM - 6:00 PM" -> OperatingHours(480, 1080)
        """
        ...
