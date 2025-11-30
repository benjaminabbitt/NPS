"""
Operating hours parsing and validation utilities.

Single source of truth for parsing operating hours from various formats.
"""
import re
from dataclasses import dataclass
from typing import Optional, Dict, Any, Union


# Default operating hours (8 AM - 5 PM) per CLAUDE.md
DEFAULT_OPENS_MINUTES = 8 * 60   # 8:00 AM = 480 minutes
DEFAULT_CLOSES_MINUTES = 17 * 60  # 5:00 PM = 1020 minutes


@dataclass
class ParsedHours:
    """Parsed operating hours in minutes from midnight."""
    opens: int  # Minutes from midnight (e.g., 540 = 9:00 AM)
    closes: int  # Minutes from midnight (e.g., 1020 = 5:00 PM)

    @property
    def opens_hour(self) -> float:
        """Opening time as decimal hour (e.g., 9.5 = 9:30 AM)"""
        return self.opens / 60.0

    @property
    def closes_hour(self) -> float:
        """Closing time as decimal hour (e.g., 17.0 = 5:00 PM)"""
        return self.closes / 60.0

    def is_open_at(self, minutes_from_midnight: int) -> bool:
        """Check if the site is open at the given time."""
        return self.opens <= minutes_from_midnight <= self.closes

    def format_time_range(self) -> str:
        """Format as human-readable string like '9:00 AM - 5:00 PM'"""
        return f"{_format_time(self.opens)} - {_format_time(self.closes)}"


def parse_operating_hours(
    hours_data: Optional[Union[Dict[str, Any], 'ParsedHours']]
) -> ParsedHours:
    """
    Parse operating hours from various formats.

    Handles:
    - Dict with 'opens'/'closes' as int (minutes) or string ('9:00 AM')
    - ParsedHours object (pass-through)
    - None (returns default hours)

    Args:
        hours_data: Operating hours in any supported format

    Returns:
        ParsedHours with opens/closes in minutes from midnight

    Examples:
        >>> parse_operating_hours({'opens': 540, 'closes': 1020})
        ParsedHours(opens=540, closes=1020)

        >>> parse_operating_hours({'opens': '9:00 AM', 'closes': '5:00 PM'})
        ParsedHours(opens=540, closes=1020)

        >>> parse_operating_hours(None)
        ParsedHours(opens=480, closes=1020)  # Default 8 AM - 5 PM
    """
    if hours_data is None:
        return ParsedHours(opens=DEFAULT_OPENS_MINUTES, closes=DEFAULT_CLOSES_MINUTES)

    if isinstance(hours_data, ParsedHours):
        return hours_data

    if not isinstance(hours_data, dict):
        return ParsedHours(opens=DEFAULT_OPENS_MINUTES, closes=DEFAULT_CLOSES_MINUTES)

    opens = _parse_time_value(hours_data.get('opens'), DEFAULT_OPENS_MINUTES)
    closes = _parse_time_value(hours_data.get('closes'), DEFAULT_CLOSES_MINUTES)

    return ParsedHours(opens=opens, closes=closes)


def _parse_time_value(value: Optional[Union[int, str]], default: int) -> int:
    """
    Parse a single time value (opens or closes).

    Args:
        value: Time as int (minutes) or string ('9:00 AM', '17:00')
        default: Default value if parsing fails

    Returns:
        Time in minutes from midnight
    """
    if value is None:
        return default

    # Already in minutes
    if isinstance(value, int):
        return value

    # String format
    if isinstance(value, str):
        parsed = parse_time_string(value)
        return parsed if parsed is not None else default

    return default


def parse_time_string(time_str: str) -> Optional[int]:
    """
    Parse time string to minutes from midnight.

    Supports:
    - 12-hour format: '9:00 AM', '5:30 PM', '12:00 PM'
    - 24-hour format: '09:00', '17:30', '00:00'

    Args:
        time_str: Time string to parse

    Returns:
        Minutes from midnight, or None if parsing fails
    """
    if not time_str:
        return None

    time_str = time_str.strip().upper()

    # Try 12-hour format with AM/PM
    match = re.match(r'(\d{1,2}):?(\d{2})?\s*(AM|PM)', time_str)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2)) if match.group(2) else 0
        period = match.group(3)

        if period == 'PM' and hours != 12:
            hours += 12
        elif period == 'AM' and hours == 12:
            hours = 0

        return hours * 60 + minutes

    # Try 24-hour format
    match = re.match(r'(\d{1,2}):(\d{2})', time_str)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        if 0 <= hours <= 23 and 0 <= minutes <= 59:
            return hours * 60 + minutes

    return None


def _format_time(minutes: int) -> str:
    """Format minutes from midnight as 12-hour time string."""
    hours = minutes // 60
    mins = minutes % 60
    period = 'AM' if hours < 12 else 'PM'

    if hours == 0:
        hours = 12
    elif hours > 12:
        hours -= 12

    if mins == 0:
        return f"{hours} {period}"
    return f"{hours}:{mins:02d} {period}"


def check_operating_hours_violation(
    arrival_minutes: int,
    hours: Optional[ParsedHours],
    always_available: bool = False
) -> bool:
    """
    Check if an arrival time violates operating hours.

    Args:
        arrival_minutes: Arrival time in minutes from midnight
        hours: Parsed operating hours (None = use defaults)
        always_available: If True, site is always accessible

    Returns:
        True if there is a violation (arrived outside hours)
    """
    if always_available:
        return False

    if hours is None:
        hours = ParsedHours(opens=DEFAULT_OPENS_MINUTES, closes=DEFAULT_CLOSES_MINUTES)

    return not hours.is_open_at(arrival_minutes)
