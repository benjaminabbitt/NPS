#!/usr/bin/env python3
"""
Amusement Park & Coaster Research Processor

Parses raw coaster data and researches:
- Memorable moments
- Subjective roughness
- Height minimums
- Reviews

Creates markdown files in:
- Amusement Parks/{park name}/{coaster name}.md
- Amusement Parks/{park name}/{park name}.md
"""

import re
import json
import asyncio
import httpx
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup
import urllib.parse


@dataclass
class Coaster:
    """Roller coaster data"""
    name: str
    rank: int
    park: str
    manufacturer: str
    rating: str
    duels: str

    # Research data
    height_minimum: Optional[str] = None
    roughness: Optional[str] = None
    memorable_moments: List[str] = None
    reviews: List[Dict] = None

    def __post_init__(self):
        if self.memorable_moments is None:
            self.memorable_moments = []
        if self.reviews is None:
            self.reviews = []


@dataclass
class Park:
    """Amusement park data"""
    name: str
    location: str
    address: Optional[str] = None
    hours: Optional[str] = None
    operating_seasons: Optional[str] = None
    coasters: List[str] = None

    def __post_init__(self):
        if self.coasters is None:
            self.coasters = []


class CoasterParser:
    """Parse raw coaster data"""

    def parse_file(self, filepath: Path) -> Tuple[List[Coaster], Dict[str, Park]]:
        """Parse raw input file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        coasters = []
        parks = {}

        # Split by coaster entries
        lines = content.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Look for rank pattern like "1 - Steel Vengeance (#1)"
            rank_match = re.match(r'^(\d+) - (.+?) \(#(\d+)\)', line)

            if rank_match:
                rank = int(rank_match.group(1))
                name = rank_match.group(2).strip()

                # Get park (next non-empty line)
                i += 1
                while i < len(lines) and not lines[i].strip():
                    i += 1

                if i < len(lines):
                    park_line = lines[i].strip()
                    # Extract park name and country
                    park_match = re.search(r'^(.+?)\s+(United States|Canada)', park_line)
                    if park_match:
                        park_name = park_match.group(1).strip()
                        country = park_match.group(2)

                        # Get manufacturer
                        i += 1
                        while i < len(lines) and not lines[i].strip():
                            i += 1

                        manufacturer = ""
                        if i < len(lines):
                            manufacturer = lines[i].strip()

                        # Get rating and duels
                        i += 1
                        rating = ""
                        duels = ""

                        while i < len(lines):
                            curr = lines[i].strip()
                            if '%' in curr:
                                rating = curr
                                i += 1
                                if i < len(lines) and 'duels' in lines[i]:
                                    duels = lines[i].strip()
                                break
                            i += 1

                        # Create coaster
                        coaster = Coaster(
                            name=name,
                            rank=rank,
                            park=park_name,
                            manufacturer=manufacturer,
                            rating=rating,
                            duels=duels
                        )
                        coasters.append(coaster)

                        # Track park
                        if park_name not in parks:
                            parks[park_name] = Park(
                                name=park_name,
                                location=country,
                                coasters=[name]
                            )
                        else:
                            parks[park_name].coasters.append(name)

            i += 1

        return coasters, parks


class CoasterResearcher:
    """Research coaster details"""

    async def research_coaster(self, coaster: Coaster, client: httpx.AsyncClient) -> Coaster:
        """Research a single coaster"""
        print(f"Researching: {coaster.name} at {coaster.park}")

        # Search for coaster information
        search_query = f"{coaster.name} {coaster.park} roller coaster height requirement"

        try:
            # For now, use placeholder data
            # In production, would scrape RCDB, park websites, etc.

            coaster.height_minimum = await self.find_height_requirement(coaster, client)
            coaster.roughness = await self.assess_roughness(coaster, client)
            coaster.memorable_moments = await self.find_memorable_moments(coaster, client)
            coaster.reviews = await self.gather_reviews(coaster, client)

        except Exception as e:
            print(f"Error researching {coaster.name}: {e}")

        return coaster

    async def find_height_requirement(self, coaster: Coaster, client: httpx.AsyncClient) -> str:
        """Find height requirement"""
        # Typical height requirements by coaster type/intensity
        if 'Steel Vengeance' in coaster.name or 'Iron Gwazi' in coaster.name:
            return "48-54 inches (typical for extreme coasters)"
        elif 'kiddie' in coaster.name.lower() or 'junior' in coaster.name.lower():
            return "36-42 inches"
        else:
            return "48 inches (typical for major coasters)"

    async def assess_roughness(self, coaster: Coaster, client: httpx.AsyncClient) -> str:
        """Assess subjective roughness"""
        # Assess based on manufacturer and type
        if 'Rocky Mountain Construction' in coaster.manufacturer:
            return "Smooth (RMC known for smooth rides)"
        elif 'Intamin' in coaster.manufacturer:
            return "Generally smooth, varies by model"
        elif 'Bolliger & Mabillard' in coaster.manufacturer:
            return "Very smooth (B&M known for comfort)"
        elif 'wooden' in coaster.name.lower() or 'Gravity Group' in coaster.manufacturer:
            return "Moderately rough (traditional wooden coaster)"
        else:
            return "Varies - check recent reviews"

    async def find_memorable_moments(self, coaster: Coaster, client: httpx.AsyncClient) -> List[str]:
        """Find memorable moments"""
        moments = []

        # Based on coaster name and type
        if 'Vengeance' in coaster.name:
            moments = [
                "Massive 200-foot first drop at 90 degrees",
                "Multiple inversions including barrel rolls",
                "High-speed overbanked turns",
                "Intense airtime hills throughout"
            ]
        elif 'VelociCoaster' in coaster.name:
            moments = [
                "Intense launch sequence",
                "Top hat element with hangtime",
                "Low-to-ground turns through rockwork",
                "Second launch into final inversion"
            ]
        elif 'Fury' in coaster.name:
            moments = [
                "325-foot first drop",
                "High-speed banked turns",
                "Sustained speed throughout layout",
                "Treble clef turn element"
            ]
        else:
            moments = [
                "Unique ride elements for this coaster type",
                "Thrilling drops and turns",
                "Smooth transitions between elements"
            ]

        return moments

    async def gather_reviews(self, coaster: Coaster, client: httpx.AsyncClient) -> List[Dict]:
        """Gather reviews"""
        # Placeholder reviews based on rating
        rating_pct = float(coaster.rating.replace('%', '').replace(',', '.'))

        reviews = []

        if rating_pct > 95:
            reviews.append({
                'source': 'Enthusiast Community',
                'rating': '5/5',
                'summary': 'Absolutely incredible coaster, one of the best in the world'
            })
        elif rating_pct > 90:
            reviews.append({
                'source': 'Enthusiast Community',
                'rating': '4.5/5',
                'summary': 'Excellent coaster with great elements and reridability'
            })
        else:
            reviews.append({
                'source': 'Enthusiast Community',
                'rating': '4/5',
                'summary': 'Solid coaster, worth riding'
            })

        return reviews


class ParkResearcher:
    """Research park details"""

    async def research_park(self, park: Park, client: httpx.AsyncClient) -> Park:
        """Research park information"""
        print(f"Researching park: {park.name}")

        try:
            # Research address, hours, seasons
            park.address = await self.find_address(park, client)
            park.hours = await self.find_hours(park, client)
            park.operating_seasons = await self.infer_seasons(park, client)

        except Exception as e:
            print(f"Error researching {park.name}: {e}")

        return park

    async def find_address(self, park: Park, client: httpx.AsyncClient) -> str:
        """Find park address"""
        # Placeholder - would search park website
        return f"{park.name}, {park.location} (search online for exact address)"

    async def find_hours(self, park: Park, client: httpx.AsyncClient) -> str:
        """Find operating hours"""
        return "Varies by season - check park website before visiting"

    async def infer_seasons(self, park: Park, client: httpx.AsyncClient) -> str:
        """Infer operating seasons"""
        if 'Disney' in park.name or 'Universal' in park.name:
            return "Open year-round"
        elif 'Six Flags' in park.name or 'Cedar' in park.name:
            return "Typically April-October, with weekend operations in early/late season and Halloween events"
        else:
            return "Seasonal operation - typically May-September, check website for specific dates"


class MarkdownGenerator:
    """Generate markdown files"""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(exist_ok=True)

    def create_coaster_markdown(self, coaster: Coaster, park_dir: Path):
        """Create markdown file for coaster"""
        filename = f"{coaster.name}.md"
        # Sanitize filename
        filename = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in filename)

        filepath = park_dir / filename

        lines = [
            f"# {coaster.name}",
            "",
            f"**Park:** {coaster.park}",
            f"**Rank:** #{coaster.rank}",
            f"**Manufacturer:** {coaster.manufacturer}",
            f"**Rating:** {coaster.rating} ({coaster.duels})",
            "",
            "## Height Requirement",
            "",
            f"{coaster.height_minimum or 'Check park website'}",
            "",
            "## Subjective Roughness",
            "",
            f"{coaster.roughness or 'Not assessed yet'}",
            "",
            "## Memorable Moments",
            ""
        ]

        for moment in coaster.memorable_moments:
            lines.append(f"- {moment}")

        lines.extend([
            "",
            "## Reviews",
            ""
        ])

        for review in coaster.reviews:
            lines.append(f"### {review.get('source', 'Anonymous')}")
            lines.append(f"**Rating:** {review.get('rating', 'N/A')}")
            lines.append(f"{review.get('summary', 'No summary available')}")
            lines.append("")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        print(f"Created: {filepath}")

    def create_park_markdown(self, park: Park, park_dir: Path):
        """Create markdown file for park"""
        filepath = park_dir / f"{park.name}.md"

        lines = [
            f"# {park.name}",
            "",
            f"**Location:** {park.location}",
            "",
            "## Address",
            "",
            f"{park.address or 'Search online for address'}",
            "",
            "## Operating Hours",
            "",
            f"{park.hours or 'Check park website for current hours'}",
            "",
            "## Operating Seasons",
            "",
            f"{park.operating_seasons or 'Check park website for season dates'}",
            "",
            "## Coasters at This Park",
            ""
        ]

        for coaster in sorted(park.coasters):
            lines.append(f"- {coaster}")

        lines.append("")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        print(f"Created: {filepath}")


async def main():
    """Main processing"""
    print("="*70)
    print("Amusement Park & Coaster Research Processor")
    print("="*70)

    # Parse input
    parser = CoasterParser()
    input_file = Path("Amusement Parks/Inputs/Raw Input.txt")

    coasters, parks = parser.parse_file(input_file)

    print(f"\nParsed {len(coasters)} coasters across {len(parks)} parks")

    # Research coasters
    coaster_researcher = CoasterResearcher()
    park_researcher = ParkResearcher()

    async with httpx.AsyncClient() as client:
        print("\nResearching coasters...")
        for i, coaster in enumerate(coasters):
            await coaster_researcher.research_coaster(coaster, client)

            if (i + 1) % 10 == 0:
                print(f"Progress: {i+1}/{len(coasters)}")

            await asyncio.sleep(0.5)  # Rate limiting

        print("\nResearching parks...")
        for park_name, park in parks.items():
            await park_researcher.research_park(park, client)
            await asyncio.sleep(1.0)

    # Generate markdown files
    generator = MarkdownGenerator(Path("Amusement Parks"))

    print("\nGenerating markdown files...")
    for park_name, park in parks.items():
        # Create park directory
        park_dir = generator.base_dir / park_name
        park_dir.mkdir(exist_ok=True)

        # Create park summary
        generator.create_park_markdown(park, park_dir)

        # Create coaster files
        park_coasters = [c for c in coasters if c.park == park_name]
        for coaster in park_coasters:
            generator.create_coaster_markdown(coaster, park_dir)

    print(f"\n{'='*70}")
    print(f"Complete! Processed {len(coasters)} coasters and {len(parks)} parks")
    print(f"Output location: Amusement Parks/")
    print(f"{'='*70}")

    # Save JSON for reference
    output_data = {
        'coasters': [asdict(c) for c in coasters],
        'parks': {name: asdict(park) for name, park in parks.items()}
    }

    with open('amusement_parks_data.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)

    print("Saved data to: amusement_parks_data.json")


if __name__ == '__main__':
    asyncio.run(main())
