#!/usr/bin/env python3
"""
World's Largest and Amusement Park Loaders with IoC

Loads attraction data using injected dependencies.
"""
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from core.site import Site
from .types import (
    WorldsLargestAttraction,
    CoasterRide,
    FileReader,
    FrontmatterParser
)


@dataclass
class WorldsLargestData:
    """Collection of World's Largest attractions"""
    attractions: List[WorldsLargestAttraction] = field(default_factory=list)
    source_file: Optional[Path] = None


class WorldsLargestLoader:
    """
    Loads World's Largest attractions using dependency injection.
    """

    def __init__(
        self,
        file_reader: FileReader,
        frontmatter_parser: FrontmatterParser
    ):
        """
        Initialize loader with dependencies.

        Args:
            file_reader: Reads file contents
            frontmatter_parser: Parses YAML frontmatter
        """
        self.file_reader = file_reader
        self.frontmatter_parser = frontmatter_parser

    def load_from_file(self, file_path: Path) -> WorldsLargestData:
        """
        Load all World's Largest attractions from markdown file.

        Args:
            file_path: Path to World's Largest.md

        Returns:
            WorldsLargestData with all attractions
        """
        content_str = self.file_reader.read(file_path)
        _, content = self.frontmatter_parser.parse(content_str)

        attractions = []
        current_category = ""

        # Split by --- markers (each attraction)
        sections = re.split(r'\n---\n', content)

        for section in sections:
            section = section.strip()
            if not section:
                continue

            # Check if this is a category header
            category_match = re.match(r'##\s+(.+)', section)
            if category_match:
                current_category = category_match.group(1).strip()
                continue

            # Check if this section contains an attraction (starts with ###)
            if not section.startswith('###'):
                continue

            # Parse attraction
            attraction = self._parse_attraction(section, current_category)
            if attraction:
                attractions.append(attraction)

        return WorldsLargestData(attractions=attractions, source_file=file_path)

    @staticmethod
    def _parse_attraction(section_text: str, category: str) -> Optional[WorldsLargestAttraction]:
        """Parse a single World's Largest attraction entry"""
        lines = [l.strip() for l in section_text.split('\n') if l.strip()]
        if not lines:
            return None

        # First line: ### NAME, State [verification]
        title_match = re.match(r'###\s+(.+?)\s*(✓|\[[\w\s-]+\])?$', lines[0])
        if not title_match:
            return None

        name = title_match.group(1).strip()
        verification = title_match.group(2).strip() if title_match.group(2) else ""

        # Second line is often the title: **World's...**
        title = ""
        if len(lines) > 1 and lines[1].startswith('**') and lines[1].endswith('**'):
            title = lines[1].replace('**', '').strip()

        # Extract fields
        data = {
            'name': name,
            'title': title,
            'what_makes_it_largest': '',
            'address': '',
            'geocode': None,
            'hours': '',
            'fees': '',
            'history': '',
            'seasonal_info': '',
            'source': '',
            'verification': verification,
            'category': category
        }

        # Parse bold headers and their content
        current_field = None
        for line in lines:
            # Check for bold headers ending with colon
            header_match = re.match(r'\*\*([^*]+):\*\*\s*(.*)', line)
            if header_match:
                header = header_match.group(1).strip()
                value = header_match.group(2).strip()
                field_name = header.lower().replace(' ', '_').replace("'", "")

                if field_name in data:
                    current_field = field_name
                    data[field_name] = value
            elif current_field and current_field in data:
                # Accumulate multiline content
                if line and not line.startswith('**'):
                    if data[current_field]:
                        data[current_field] += ' ' + line
                    else:
                        data[current_field] = line

        # Extract GPS coordinates
        gps_match = re.search(r'(-?\d+\.\d+)°?\s*[NS],?\s*(-?\d+\.\d+)°?\s*[EW]', section_text)
        if gps_match:
            data['geocode'] = (float(gps_match.group(1)), float(gps_match.group(2)))

        return WorldsLargestAttraction(**data)


@dataclass
class AmusementParkData:
    """Amusement park with coasters and tracking"""
    site: Site  # Park location
    location: str = ""
    address: str = ""
    operating_hours: str = ""
    operating_seasons: str = ""

    coasters: List[CoasterRide] = field(default_factory=list)

    directory: Optional[Path] = None
    main_file: Optional[Path] = None


class AmusementParkLoader:
    """
    Loads amusement park data using dependency injection.
    """

    def __init__(
        self,
        file_reader: FileReader,
        frontmatter_parser: FrontmatterParser
    ):
        """
        Initialize loader with dependencies.

        Args:
            file_reader: Reads file contents
            frontmatter_parser: Parses YAML frontmatter
        """
        self.file_reader = file_reader
        self.frontmatter_parser = frontmatter_parser

    def load_from_directory(self, park_dir: Path) -> AmusementParkData:
        """
        Load amusement park data from directory.

        Args:
            park_dir: Path to park directory

        Returns:
            AmusementParkData with park and coaster info
        """
        park_dir = Path(park_dir)
        park_name = park_dir.name

        # Find main park file
        main_file = park_dir / f"{park_name}.md"
        if not main_file.exists():
            raise FileNotFoundError(f"Park file not found: {main_file}")

        # Parse main park file
        park_data = self._parse_park_file(main_file)

        # Find all coaster files
        coaster_files = [f for f in park_dir.glob("*.md") if f.name != main_file.name]

        coasters = []
        for coaster_file in coaster_files:
            coaster = self._parse_coaster_file(coaster_file, park_name)
            if coaster:
                coasters.append(coaster)

        # Create Site instance (geocode TBD - would need to be added to park files)
        site = Site(
            name=park_name,
            lat=0.0,
            lon=0.0,
            address=park_data.get('address', '')
        )

        return AmusementParkData(
            site=site,
            location=park_data.get('location', ''),
            address=park_data.get('address', ''),
            operating_hours=park_data.get('operating_hours', ''),
            operating_seasons=park_data.get('operating_seasons', ''),
            coasters=coasters,
            directory=park_dir,
            main_file=main_file
        )

    def _parse_park_file(self, park_file: Path) -> Dict[str, str]:
        """Parse main amusement park file"""
        content_str = self.file_reader.read(park_file)
        _, content = self.frontmatter_parser.parse(content_str)

        data = {
            'location': '',
            'address': '',
            'operating_hours': '',
            'operating_seasons': ''
        }

        # Extract bold fields
        location_match = re.search(r'\*\*Location:\*\*\s*(.+)', content)
        if location_match:
            data['location'] = location_match.group(1).strip()

        # Extract sections
        sections = re.split(r'\n## ', content)
        for section in sections:
            title = section.split('\n')[0].strip()
            body = '\n'.join(section.split('\n')[1:]).strip()

            if title == 'Address':
                data['address'] = body
            elif 'Operating Hours' in title:
                data['operating_hours'] = body
            elif 'Operating Seasons' in title:
                data['operating_seasons'] = body

        return data

    def _parse_coaster_file(self, coaster_file: Path, park_name: str) -> Optional[CoasterRide]:
        """Parse individual coaster file"""
        content_str = self.file_reader.read(coaster_file)
        _, content = self.frontmatter_parser.parse(content_str)

        # Extract coaster name from title
        name_match = re.match(r'#\s+(.+)', content)
        if not name_match:
            return None

        name = name_match.group(1).strip()

        data = {
            'name': name,
            'park_name': park_name,
            'rank': '',
            'manufacturer': '',
            'rating': '',
            'height_requirement': '',
            'roughness': '',
            'memorable_moments': [],
            'reviews': '',
            'file_path': coaster_file
        }

        # Extract bold metadata fields
        rank_match = re.search(r'\*\*Rank:\*\*\s*#?(\d+)', content)
        if rank_match:
            data['rank'] = rank_match.group(1)

        manufacturer_match = re.search(r'\*\*Manufacturer:\*\*\s*(.+)', content)
        if manufacturer_match:
            data['manufacturer'] = manufacturer_match.group(1).strip()

        rating_match = re.search(r'\*\*Rating:\*\*\s*(.+)', content)
        if rating_match:
            data['rating'] = rating_match.group(1).strip()

        # Extract sections
        sections = re.split(r'\n## ', content)
        for section in sections:
            title = section.split('\n')[0].strip()
            body = '\n'.join(section.split('\n')[1:]).strip()

            if 'Height Requirement' in title:
                data['height_requirement'] = body
            elif 'Roughness' in title:
                data['roughness'] = body
            elif 'Memorable Moments' in title:
                # Extract bullet points
                moments = re.findall(r'-\s+(.+)', body)
                data['memorable_moments'] = moments
            elif 'Reviews' in title:
                data['reviews'] = body

        return CoasterRide(**data)
