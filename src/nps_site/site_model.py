"""NPS Site data model for parsing user-data.md files."""
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Protocol, Union, runtime_checkable


# Constant: time for cancellation stamp collection regardless of number of stamps
STAMP_COLLECTION_MINUTES = 15


@runtime_checkable
class VisitationSite(Protocol):
    """
    Protocol for visitation site data.

    Any class implementing this protocol can be used in trip planning
    to determine whether to skip a site and how much time to allocate.
    """

    def should_skip(self) -> bool:
        """
        Determine if this site should be skipped in trip planning.

        Returns:
            True if site should be skipped (e.g., already visited)
        """
        ...

    def total_time(self) -> int:
        """
        Calculate total time needed for selected activities at this site.

        Returns:
            Total time in minutes for all selected activities
        """
        ...


def parse_duration(text: str) -> int:
    """
    Parse duration from activity text.

    Supports formats:
    - "30 minutes" -> 30
    - "30-60 minutes" -> 45 (average)
    - "1 hour" -> 60
    - "1-1.5 hours" -> 75 (average)
    - "1.5 hours" -> 90

    Args:
        text: Text containing duration information

    Returns:
        Duration in minutes, or 0 if not found
    """
    # Try range of hours first (e.g., "1-1.5 hours")
    hours_range = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*hours?", text, re.IGNORECASE)
    if hours_range:
        low = float(hours_range.group(1))
        high = float(hours_range.group(2))
        return int((low + high) / 2 * 60)

    # Try single hours (e.g., "1 hour" or "1.5 hours")
    single_hours = re.search(r"(\d+(?:\.\d+)?)\s*hours?", text, re.IGNORECASE)
    if single_hours:
        return int(float(single_hours.group(1)) * 60)

    # Try range of minutes (e.g., "30-60 minutes")
    minutes_range = re.search(r"(\d+)\s*-\s*(\d+)\s*minutes?", text, re.IGNORECASE)
    if minutes_range:
        low = int(minutes_range.group(1))
        high = int(minutes_range.group(2))
        return (low + high) // 2

    # Try single minutes (e.g., "30 minutes")
    single_minutes = re.search(r"(\d+)\s*minutes?", text, re.IGNORECASE)
    if single_minutes:
        return int(single_minutes.group(1))

    return 0


@dataclass
class Activity:
    """An activity item from a site."""

    name: str
    duration_minutes: int
    selected: bool = False
    reference_id: Optional[str] = None

    @classmethod
    def from_markdown(cls, line: str) -> "Activity":
        """
        Parse an activity from a markdown checkbox line.

        Format: "- [ ] Activity Name (30-60 minutes) [ref_id]"
        or:     "- [x] Activity Name (30-60 minutes) [ref_id]"
        """
        # Check if selected
        selected = "[x]" in line.lower()

        # Extract reference ID if present
        ref_match = re.search(r"\[([a-f0-9]{6})\]$", line.strip())
        reference_id = ref_match.group(1) if ref_match else None

        # Remove the checkbox and reference from the line for name extraction
        content = re.sub(r"^-\s*\[[x ]\]\s*", "", line.strip(), flags=re.IGNORECASE)
        content = re.sub(r"\s*\[[a-f0-9]{6}\]$", "", content)

        # Extract duration from parentheses
        duration = parse_duration(content)

        # Extract name (everything before the first parenthesis with duration)
        name_match = re.match(r"^([^(]+)", content)
        name = name_match.group(1).strip() if name_match else content.strip()

        return cls(
            name=name,
            duration_minutes=duration,
            selected=selected,
            reference_id=reference_id,
        )


@dataclass
class CancellationStamp:
    """A cancellation stamp location."""

    location: str
    address: str
    selected: bool = False
    reference_id: Optional[str] = None

    @classmethod
    def from_markdown(cls, line: str) -> "CancellationStamp":
        """
        Parse a stamp location from a markdown checkbox line.

        Format: "- [ ] Location Name (Address info) [ref_id]"
        or:     "- [x] Location Name (Address) - Notes [ref_id]"
        """
        # Check if selected
        selected = "[x]" in line.lower()

        # Extract reference ID if present
        ref_match = re.search(r"\[([a-f0-9]{6})\]$", line.strip())
        reference_id = ref_match.group(1) if ref_match else None

        # Remove the checkbox and reference from the line
        content = re.sub(r"^-\s*\[[x ]\]\s*", "", line.strip(), flags=re.IGNORECASE)
        content = re.sub(r"\s*\[[a-f0-9]{6}\]$", "", content)

        # Extract location name and address
        # Format: "Location Name (Address info)" or "Location Name (Address) - Notes"
        paren_match = re.match(r"^([^(]+)\(([^)]+)\)", content)
        if paren_match:
            location = paren_match.group(1).strip()
            address = paren_match.group(2).strip()
        else:
            # No parentheses, use whole content as location
            location = content.strip()
            address = ""

        return cls(
            location=location,
            address=address,
            selected=selected,
            reference_id=reference_id,
        )


@dataclass
class SiteData:
    """Complete data model for an NPS site from user-data.md."""

    name: str
    visited: bool
    cancellation_stamps: List[CancellationStamp]
    key_activities: List[Activity]
    hidden_gems: List[Activity]
    also_nearby: List[Activity]

    def calculate_selected_duration(self) -> int:
        """
        Calculate total duration of selected items.

        Rules:
        - Stamp collection is always 15 minutes flat if any stamp is selected
        - Activity durations are summed for all selected activities
        - All categories (key activities, hidden gems, nearby) are included

        Returns:
            Total duration in minutes
        """
        total = 0

        # Add stamp time if any stamp selected (flat 15 minutes)
        if any(stamp.selected for stamp in self.cancellation_stamps):
            total += STAMP_COLLECTION_MINUTES

        # Sum selected activities from all categories
        for activity in self.key_activities:
            if activity.selected:
                total += activity.duration_minutes

        for activity in self.hidden_gems:
            if activity.selected:
                total += activity.duration_minutes

        for activity in self.also_nearby:
            if activity.selected:
                total += activity.duration_minutes

        return total

    # VisitationSite protocol methods

    def should_skip(self) -> bool:
        """
        Determine if this site should be skipped in trip planning.

        Returns:
            True if site has already been visited
        """
        return self.visited

    def total_time(self) -> int:
        """
        Calculate total time needed for selected activities at this site.

        Returns:
            Total time in minutes for all selected activities
        """
        return self.calculate_selected_duration()


def parse_user_data(source: Union[str, Path]) -> SiteData:
    """
    Parse a user-data.md file or content string into a SiteData model.

    Args:
        source: Either a file path (Path) or content string

    Returns:
        Populated SiteData model
    """
    # Get content
    if isinstance(source, Path):
        content = source.read_text()
    elif isinstance(source, str) and not source.startswith("#"):
        # Looks like a file path string
        content = Path(source).read_text()
    else:
        content = source

    lines = content.split("\n")

    # Extract site name from first line
    name = ""
    visited = False
    cancellation_stamps: List[CancellationStamp] = []
    key_activities: List[Activity] = []
    hidden_gems: List[Activity] = []
    also_nearby: List[Activity] = []

    current_section = None

    for line in lines:
        line_stripped = line.strip()

        # Parse site name from H1
        if line_stripped.startswith("# ") and not name:
            name = line_stripped[2:].strip()
            continue

        # Parse visited checkbox
        if "- [x] Visited" in line or "- [ ] Visited" in line:
            visited = "[x]" in line.lower()
            continue

        # Track current section
        if line_stripped.startswith("## "):
            section_name = line_stripped[3:].strip().lower()
            if "cancellation" in section_name or "stamp" in section_name:
                current_section = "stamps"
            elif "key activit" in section_name:
                current_section = "key"
            elif "hidden gem" in section_name:
                current_section = "hidden"
            elif "also nearby" in section_name or "nearby" in section_name:
                current_section = "nearby"
            else:
                current_section = None
            continue

        # Parse checkbox items in sections
        if line_stripped.startswith("- ["):
            if current_section == "stamps":
                try:
                    stamp = CancellationStamp.from_markdown(line_stripped)
                    cancellation_stamps.append(stamp)
                except Exception:
                    pass
            elif current_section == "key":
                try:
                    activity = Activity.from_markdown(line_stripped)
                    key_activities.append(activity)
                except Exception:
                    pass
            elif current_section == "hidden":
                try:
                    activity = Activity.from_markdown(line_stripped)
                    hidden_gems.append(activity)
                except Exception:
                    pass
            elif current_section == "nearby":
                try:
                    activity = Activity.from_markdown(line_stripped)
                    also_nearby.append(activity)
                except Exception:
                    pass

    return SiteData(
        name=name,
        visited=visited,
        cancellation_stamps=cancellation_stamps,
        key_activities=key_activities,
        hidden_gems=hidden_gems,
        also_nearby=also_nearby,
    )
