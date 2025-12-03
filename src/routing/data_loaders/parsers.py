#!/usr/bin/env python3
"""
Concrete implementations of parser protocols
"""
import re
import frontmatter as fm
import mistune
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

from .types import OperatingHours


class StandardFileReader:
    """Standard file reader implementation"""

    def read(self, file_path: Path) -> str:
        """Read file contents as UTF-8 string"""
        return file_path.read_text(encoding='utf-8')


class StandardFrontmatterParser:
    """Standard frontmatter parser using python-frontmatter"""

    def parse(self, content: str) -> Tuple[Dict[str, Any], str]:
        """Parse YAML frontmatter and markdown content"""
        post = fm.loads(content)
        return (post.metadata, post.content)


class MistuneMarkdownParser:
    """Markdown parser using mistune to extract sections and list items"""

    class ListRenderer(mistune.HTMLRenderer):
        """Custom renderer to extract structured list data"""

        def __init__(self):
            super().__init__()
            self.current_section = None
            self.sections = {}
            self.list_items = []

        def heading(self, text, level, **attrs):
            """Capture section headings"""
            if level == 2:
                # Save previous section's list items
                if self.current_section and self.list_items:
                    self.sections[self.current_section] = self.list_items
                    self.list_items = []
                # Start new section
                self.current_section = text.strip().rstrip(':')
            return f"<h{level}>{text}</h{level}>"

        def list_item(self, text, **attrs):
            """Capture list items"""
            if self.current_section:
                self.list_items.append(text)
            return f"<li>{text}</li>"

        def finalize(self):
            """Finalize by saving last section"""
            if self.current_section and self.list_items:
                self.sections[self.current_section] = self.list_items
            return self.sections

    def parse(self, content: str) -> Dict[str, List[str]]:
        """Parse markdown into sections with list items"""
        renderer = self.ListRenderer()
        markdown = mistune.Markdown(renderer=renderer)
        markdown(content)
        return renderer.finalize()


class RegexDurationParser:
    """Duration parser using regex patterns"""

    def parse(self, duration_str: str) -> float:
        """
        Parse duration string to hours.

        Examples:
            "4 hours" -> 4.0
            "2-3 hours" -> 2.5 (average)
            "30 minutes" -> 0.5
            "1.5 hours" -> 1.5
        """
        duration_str = duration_str.lower().strip()

        # Range: "2-3 hours" -> average
        range_match = re.search(r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*hours?', duration_str)
        if range_match:
            low = float(range_match.group(1))
            high = float(range_match.group(2))
            return (low + high) / 2

        # Single value: "4 hours"
        hours_match = re.search(r'(\d+(?:\.\d+)?)\s*hours?', duration_str)
        if hours_match:
            return float(hours_match.group(1))

        # Minutes: "30 minutes"
        minutes_match = re.search(r'(\d+)\s*(?:min|minutes?)', duration_str)
        if minutes_match:
            return float(minutes_match.group(1)) / 60

        return 0.0


class RegexOperatingHoursParser:
    """Operating hours parser using regex patterns"""

    def parse(self, hours_str: str) -> Optional[OperatingHours]:
        """
        Parse hours string to OperatingHours.

        Examples:
            "9:00 AM - 5:00 PM" -> OperatingHours(540, 1020)
            "Daily 8:00 AM - 6:00 PM" -> OperatingHours(480, 1080)
        """
        # Match time patterns like "9:00 AM - 5:00 PM"
        pattern = r'(\d{1,2}):(\d{2})\s*(AM|PM)?\s*-\s*(\d{1,2}):(\d{2})\s*(AM|PM)?'
        match = re.search(pattern, hours_str, re.IGNORECASE)

        if not match:
            return None

        # Parse opening time
        open_hour = int(match.group(1))
        open_min = int(match.group(2))
        open_period = (match.group(3) or '').upper()

        if open_period == 'PM' and open_hour != 12:
            open_hour += 12
        elif open_period == 'AM' and open_hour == 12:
            open_hour = 0

        opens = open_hour * 60 + open_min

        # Parse closing time
        close_hour = int(match.group(4))
        close_min = int(match.group(5))
        close_period = (match.group(6) or '').upper()

        if close_period == 'PM' and close_hour != 12:
            close_hour += 12
        elif close_period == 'AM' and close_hour == 12:
            close_hour = 0

        closes = close_hour * 60 + close_min

        return OperatingHours(opens=opens, closes=closes)
