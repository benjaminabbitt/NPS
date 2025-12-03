#!/usr/bin/env python3
"""
NPS Site Data Loader with IoC

Loads NPS site data from Enhanced Data directory using injected dependencies.
"""
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from core.site import Site
from .types import (
    CancellationStamp,
    Activity,
    FileReader,
    FrontmatterParser,
    MarkdownParser,
    DurationParser
)


@dataclass
class NPSSiteData:
    """
    Enhanced NPS Site with integrated research and user data.

    Combines information from:
    - [Site Name].md: Comprehensive research report
    - user-data.md: User checklist and notes
    - Site class: Core geographic/timing data
    """
    # Core site information
    site: Site

    # User tracking
    visited: bool = False
    review_notes: str = ""

    # Site components
    stamps: List[CancellationStamp] = field(default_factory=list)
    key_activities: List[Activity] = field(default_factory=list)
    hidden_gems: List[Activity] = field(default_factory=list)
    also_nearby: List[Activity] = field(default_factory=list)

    # Metadata
    total_recommended_time_hours: float = 0.0

    # File paths
    directory: Optional[Path] = None
    main_report_path: Optional[Path] = None
    user_data_path: Optional[Path] = None


class NPSSiteLoader:
    """
    Loads NPS site data using dependency injection.

    All parsing dependencies are injected, making this class
    highly testable and following IoC principles.
    """

    def __init__(
        self,
        file_reader: FileReader,
        frontmatter_parser: FrontmatterParser,
        markdown_parser: MarkdownParser,
        duration_parser: DurationParser
    ):
        """
        Initialize NPS loader with dependencies.

        Args:
            file_reader: Reads file contents
            frontmatter_parser: Parses YAML frontmatter
            markdown_parser: Parses markdown into sections
            duration_parser: Parses duration strings
        """
        self.file_reader = file_reader
        self.frontmatter_parser = frontmatter_parser
        self.markdown_parser = markdown_parser
        self.duration_parser = duration_parser

    def load_from_directory(
        self,
        site_dir: Path,
        existing_site: Optional[Site] = None
    ) -> NPSSiteData:
        """
        Load NPSSiteData from site directory.

        Args:
            site_dir: Path to site directory
            existing_site: Optional Site instance

        Returns:
            NPSSiteData with all data loaded
        """
        site_dir = Path(site_dir)
        site_name = site_dir.name

        # Find markdown files
        main_report = site_dir / f"{site_name}.md"
        user_data = site_dir / "user-data.md"

        if not main_report.exists():
            raise FileNotFoundError(f"Main report not found: {main_report}")
        if not user_data.exists():
            raise FileNotFoundError(f"User data not found: {user_data}")

        # Parse both files
        main_data = self._parse_main_report(main_report)
        user_checklist = self._parse_user_data(user_data)

        # Create or use provided Site instance
        if existing_site:
            site = existing_site
        else:
            # Extract geocode from YAML frontmatter or first stamp
            lat, lon = 0.0, 0.0
            if main_data.get('geocode'):
                lat, lon = main_data['geocode']
            elif main_data['stamps']:
                first_stamp = main_data['stamps'][0]
                if first_stamp.geocode:
                    lat, lon = first_stamp.geocode

            site = Site(
                name=site_name,
                lat=lat,
                lon=lon,
                address=main_data['stamps'][0].address if main_data['stamps'] else ""
            )

        # Merge checklist states from user data
        self._merge_checklist_states(main_data, user_checklist)

        return NPSSiteData(
            site=site,
            visited=user_checklist['visited'],
            review_notes=user_checklist['review_notes'],
            stamps=main_data['stamps'],
            key_activities=main_data['key_activities'],
            hidden_gems=main_data['hidden_gems'],
            also_nearby=main_data['also_nearby'],
            total_recommended_time_hours=main_data['total_time'],
            directory=site_dir,
            main_report_path=main_report,
            user_data_path=user_data
        )

    def _parse_main_report(self, report_path: Path) -> Dict[str, Any]:
        """Parse main research report"""
        # Read and parse frontmatter
        content_str = self.file_reader.read(report_path)
        metadata, content = self.frontmatter_parser.parse(content_str)

        data = {
            'stamps': [],
            'key_activities': [],
            'hidden_gems': [],
            'also_nearby': [],
            'total_time': 0.0,
            'geocode': None
        }

        # Extract geocode from YAML frontmatter
        if 'geocode' in metadata and 'visitor_center' in metadata['geocode']:
            coords = metadata['geocode']['visitor_center']
            if isinstance(coords, list) and len(coords) == 2:
                data['geocode'] = (float(coords[0]), float(coords[1]))

        # Parse markdown content into sections
        sections = self.markdown_parser.parse(content)

        # Extract structured data from sections
        for section_title, items in sections.items():
            if 'Cancellation Stamp' in section_title:
                data['stamps'] = self._parse_stamps(items)
            elif section_title == 'Key Activities':
                data['key_activities'] = self._parse_activities(items)
            elif section_title == 'Hidden Gems':
                data['hidden_gems'] = self._parse_activities(items)
            elif section_title == 'Also Nearby':
                data['also_nearby'] = self._parse_activities(items, is_nearby=True)

        # Extract total recommended time
        time_match = re.search(
            r'\*\*Total recommended visit time[^:]*:\s*([\d.-]+)\s*hours?\*\*',
            content,
            re.IGNORECASE
        )
        if time_match:
            data['total_time'] = self.duration_parser.parse(time_match.group(1) + ' hours')

        return data

    def _parse_stamps(self, items: List[str]) -> List[CancellationStamp]:
        """Parse cancellation stamp entries from list items"""
        stamps = []

        for item in items:
            # Match: **Location Name** (Address; Hours; Phone)
            pattern = r'<strong>([^<]+)</strong>\s*\(([^)]+)\)'
            match = re.search(pattern, item)

            if not match:
                # Try plain text bold: **Name** (details)
                pattern = r'\*\*([^*]+)\*\*\s*\(([^)]+)\)'
                match = re.search(pattern, item)

            if match:
                location = match.group(1).strip()
                details = match.group(2)

                # Split details by semicolon
                parts = [p.strip() for p in details.split(';')]
                address = parts[0] if parts else ""
                hours = parts[1] if len(parts) > 1 else ""
                phone = parts[2] if len(parts) > 2 else ""

                # Extract geocode from address if present
                geocode = None
                geocode_match = re.search(r'(-?\d+\.\d+),\s*(-?\d+\.\d+)', address)
                if geocode_match:
                    geocode = (float(geocode_match.group(1)), float(geocode_match.group(2)))

                stamps.append(CancellationStamp(
                    location=location,
                    address=address,
                    hours=hours,
                    phone=phone,
                    geocode=geocode
                ))

        return stamps

    def _parse_activities(self, items: List[str], is_nearby: bool = False) -> List[Activity]:
        """Parse activity entries from list items"""
        activities = []

        for item in items:
            # Match: **Activity Name** (duration) or **Activity Name** (duration, distance)
            name_pattern = r'(?:<strong>([^<]+)</strong>|\*\*([^*]+)\*\*)\s*\(([^)]+)\)'
            match = re.search(name_pattern, item)

            if not match:
                continue

            name = (match.group(1) or match.group(2)).strip()
            duration_str = match.group(3).strip()

            # Parse duration and distance
            duration = self.duration_parser.parse(duration_str)
            distance = ""

            if is_nearby and ',' in duration_str:
                parts = duration_str.split(',', 1)
                duration = self.duration_parser.parse(parts[0])
                distance = parts[1].strip()

            # Extract description and sources
            description = ""
            sources = []

            remainder = item[match.end():].strip()
            if remainder.startswith('-'):
                remainder = remainder[1:].strip()

            # Remove HTML tags
            remainder = re.sub(r'<[^>]+>', '', remainder)

            # Split by [Source:
            if '[Source:' in remainder or 'Source:' in remainder:
                desc_part = re.split(r'\[?Source:', remainder)[0].strip()
                description = desc_part
                sources = re.findall(r'https?://[^\s\]]+', remainder)
            else:
                description = remainder

            activities.append(Activity(
                name=name,
                duration_hours=duration,
                description=description,
                distance=distance,
                sources=sources
            ))

        return activities

    def _parse_user_data(self, user_data_path: Path) -> Dict[str, Any]:
        """Parse user-data.md checklist"""
        content_str = self.file_reader.read(user_data_path)
        _, content = self.frontmatter_parser.parse(content_str)

        data = {
            'visited': False,
            'stamps_checked': [],
            'activities_checked': [],
            'gems_checked': [],
            'nearby_checked': [],
            'review_notes': ''
        }

        # Check visited status
        if re.search(r'-\s*\[x\]\s*Visited', content, re.IGNORECASE):
            data['visited'] = True

        # Parse markdown into sections
        sections = self.markdown_parser.parse(content)

        # Extract checked items from each section
        for section_title, items in sections.items():
            checked_items = []
            for item in items:
                if re.search(r'\[x\]', item, re.IGNORECASE):
                    name_match = re.search(r'\[x\]\s*([^(<]+)', item, re.IGNORECASE)
                    if name_match:
                        checked_items.append(name_match.group(1).strip())

            if 'Cancellation Stamp' in section_title:
                data['stamps_checked'] = checked_items
            elif section_title == 'Key Activities':
                data['activities_checked'] = checked_items
            elif section_title == 'Hidden Gems':
                data['gems_checked'] = checked_items
            elif section_title == 'Also Nearby':
                data['nearby_checked'] = checked_items
            elif 'Review' in section_title or 'Notes' in section_title:
                section_text = '\n'.join(items)
                data['review_notes'] = re.sub(r'<[^>]+>', '', section_text).strip()

        return data

    @staticmethod
    def _merge_checklist_states(main_data: Dict[str, Any], user_checklist: Dict[str, Any]):
        """Merge completion states from user checklist into main data"""
        # Match stamps by location name
        for stamp in main_data.get('stamps', []):
            stamp.completed = NPSSiteLoader._is_checked(
                stamp.location,
                user_checklist.get('stamps_checked', [])
            )

        # Match activities by name
        for activity in main_data.get('key_activities', []):
            activity.completed = NPSSiteLoader._is_checked(
                activity.name,
                user_checklist.get('activities_checked', [])
            )

        for gem in main_data.get('hidden_gems', []):
            gem.completed = NPSSiteLoader._is_checked(
                gem.name,
                user_checklist.get('gems_checked', [])
            )

        for nearby in main_data.get('also_nearby', []):
            nearby.completed = NPSSiteLoader._is_checked(
                nearby.name,
                user_checklist.get('nearby_checked', [])
            )

    @staticmethod
    def _is_checked(item_name: str, checked_list: List[str]) -> bool:
        """Check if item name appears in checked list (fuzzy match)"""
        item_clean = item_name.lower().strip()

        for checked in checked_list:
            checked_clean = checked.lower().strip()
            if item_clean == checked_clean or item_clean in checked_clean or checked_clean in item_clean:
                return True

        return False
