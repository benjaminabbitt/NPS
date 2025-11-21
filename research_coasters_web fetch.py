#!/usr/bin/env python3
"""
Research coasters using direct RCDB links and web content analysis
"""

import asyncio
from pathlib import Path
import json
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict


@dataclass
class CoasterResearch:
    coaster_name: str
    park_name: str
    roughness: str
    roughness_sources: List[str]
    height_requirement: str
    height_sources: List[str]
    memorable_moments: List[str]
    moment_sources: List[str]


async def research_coaster_via_claude(coaster_name: str, park_name: str) -> CoasterResearch:
    """
    This is a template - actual research needs to be done via WebFetch tool
    which has better access to websites with anti-scraping measures
    """

    # Direct RCDB URL construction (common pattern)
    search_query = f"{coaster_name} {park_name} roller coaster"

    # Return placeholder that indicates manual research needed
    return CoasterResearch(
        coaster_name=coaster_name,
        park_name=park_name,
        roughness=f"Research needed: Search '{coaster_name}' on RCDB and CoasterBuzz for rider feedback on roughness/smoothness",
        roughness_sources=[],
        height_requirement=f"Research needed: Check RCDB entry for {coaster_name}",
        height_sources=[],
        memorable_moments=[
            f"Research needed: Search reviews for {coaster_name} memorable elements"
        ],
        moment_sources=[]
    )


async def create_research_tasks():
    """Create a task list for manual research with WebFetch"""

    base_dir = Path("Amusement Parks")
    park_dirs = [d for d in base_dir.iterdir() if d.is_dir() and d.name != "Inputs"]

    all_coasters = []

    # Collect all coasters
    for park_dir in park_dirs:
        park_name = park_dir.name
        park_file = park_dir / f"{park_name}.md"

        coaster_files = [f for f in park_dir.glob("*.md") if f.name != park_file.name]

        for coaster_file in coaster_files:
            coaster_name = coaster_file.stem
            all_coasters.append((coaster_name, park_name))

    # Create research task list
    task_list = []

    for coaster_name, park_name in all_coasters:
        # Create RCDB search URL
        rcdb_search = f"https://rcdb.com/qs.htm?qs={coaster_name.replace(' ', '+')}"

        task = {
            "coaster": coaster_name,
            "park": park_name,
            "research_urls": {
                "rcdb": rcdb_search,
                "coasterbuzz": f"https://coasterbuzz.com/Search?q={coaster_name.replace(' ', '+')}",
                "reddit": f"https://www.reddit.com/r/rollercoasters/search/?q={coaster_name.replace(' ', '+')}"
            },
            "needed_info": [
                "Height requirement (in inches)",
                "Roughness assessment from rider reviews",
                "3-4 memorable moments/elements",
                "Overall rider rating/sentiment"
            ]
        }

        task_list.append(task)

    # Save task list
    output_file = Path("coaster_research_tasks.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(task_list, f, indent=2)

    print(f"Created research task list for {len(task_list)} coasters")
    print(f"Saved to: {output_file}")
    print()
    print("Next steps:")
    print("  1. Use WebFetch tool to research each coaster")
    print("  2. For each coaster, fetch:")
    print("     - RCDB page for technical specs")
    print("     - CoasterBuzz reviews for rider feedback")
    print("     - Reddit discussions for authentic opinions")
    print("  3. Update markdown files with cited findings")


async def main():
    await create_research_tasks()


if __name__ == '__main__':
    asyncio.run(main())
