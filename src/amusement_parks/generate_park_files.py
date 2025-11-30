#!/usr/bin/env python3
"""
Generate structured amusement park files with geocoded addresses and coaster data.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple


def load_geocoded_data() -> Dict:
    """Load geocoded park data from JSON file."""
    geocoded_file = Path("/workspace/src/geocoding/geocoded_data.json")
    with open(geocoded_file, 'r') as f:
        data = json.load(f)
    return data.get('amusement_parks', {})


def parse_coaster_data() -> Dict[str, List[Tuple[str, str]]]:
    """
    Parse coaster data from raw input file.
    Returns dict mapping park name to list of (coaster_name, manufacturer) tuples.
    """
    input_file = Path("/workspace/1-Raw Input Data/Amusement Parks/Raw Input.txt")
    with open(input_file, 'r') as f:
        content = f.read()

    parks = {}
    lines = content.split('\n')

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Look for coaster entries (format: "Coaster Name")
        # Followed by ranking line
        # Followed by park name + "United States"
        # Followed by manufacturer

        if line and not line.startswith(('ranked', 'ratings', 'voters', 'analyzed', '1865', '602.5K', '17677', '100.4M')):
            # This might be a coaster name
            coaster_name = line

            # Check next few lines for park and manufacturer
            if i + 3 < len(lines):
                # Skip ranking line
                i += 1
                while i < len(lines) and (lines[i].strip().startswith(tuple('0123456789')) or
                                         lines[i].strip() == '' or
                                         '- ' in lines[i] and '(#' in lines[i]):
                    i += 1

                # Should be at park name now
                if i < len(lines):
                    park_line = lines[i].strip()
                    if ' United States' in park_line:
                        park_name = park_line.replace(' United States', '').strip()
                        i += 1

                        # Next should be manufacturer
                        if i < len(lines):
                            manufacturer = lines[i].strip()

                            # Clean up coaster name (remove ranking prefix if present)
                            coaster_clean = re.sub(r'^\d+\s*-\s*', '', coaster_name)
                            coaster_clean = re.sub(r'\s*\(#\d+\).*$', '', coaster_clean)

                            if park_name and coaster_clean:
                                if park_name not in parks:
                                    parks[park_name] = []
                                parks[park_name].append((coaster_clean, manufacturer))

        i += 1

    return parks


def sanitize_filename(name: str) -> str:
    """Sanitize park name for use as directory name."""
    # Replace special characters with safe alternatives
    sanitized = name.replace("'", "")
    sanitized = sanitized.replace("!", "")
    sanitized = sanitized.replace("&", "and")
    sanitized = sanitized.replace(" - ", " ")
    sanitized = sanitized.replace("  ", " ")
    return sanitized.strip()


def create_main_report(park_name: str, address: str, coords: List[float]) -> str:
    """Generate main park report markdown content."""
    lat, lon = coords

    content = f"""# {park_name}

**Address:** {address} [{lat}, {lon}]

## Park Information

*Research needed: Operating hours, admission prices, parking, season dates*

## Notable Coasters

*See user-data.md for complete coaster checklist*

## Planning Tips

*Research needed: Best visiting times, fast pass options, food recommendations*

## Nearby Attractions

*Research needed: Hotels, restaurants, other activities*

---

**Last Updated:** 2025-11-26
"""
    return content


def create_user_data(park_name: str, address: str, coords: List[float],
                    coasters: List[Tuple[str, str]]) -> str:
    """Generate user-data.md with coaster checklist."""
    lat, lon = coords

    # Sanitize park name for filename
    sanitized = sanitize_filename(park_name)
    report_filename = f"{sanitized}.md"

    content = f"""# {park_name}

[View Full Park Report]({report_filename.replace(' ', '%20')})

**Address:** {address} [{lat}, {lon}]

- [ ] Visited

## Coasters

"""

    # Add each coaster with three checkboxes
    for coaster_name, manufacturer in sorted(coasters, key=lambda x: x[0]):
        content += f"""### {coaster_name}
**Manufacturer:** {manufacturer}

- [ ] Honor Ridden
- [ ] Ben Ridden
- [ ] Amber Ridden

**Notes:**

---

"""

    content += """## Park Notes

*General observations, tips, memorable moments*

"""

    return content


def generate_all_park_files():
    """Generate all park directories and files."""
    # Load geocoded data
    geocoded_parks = load_geocoded_data()

    # Parse coaster data
    parks_coasters = parse_coaster_data()

    # Create base directory
    base_dir = Path("/workspace/2-Enhanced Data/Amusement Parks")
    base_dir.mkdir(parents=True, exist_ok=True)

    created_count = 0
    skipped_count = 0

    # Process each geocoded park
    for park_name, park_data in geocoded_parks.items():
        address = park_data['address']
        coords = park_data['coords']

        # Get coasters for this park (match by name)
        coasters = parks_coasters.get(park_name, [])

        # Create park directory
        sanitized_name = sanitize_filename(park_name)
        park_dir = base_dir / sanitized_name
        park_dir.mkdir(exist_ok=True)

        # Generate main report
        main_report = create_main_report(park_name, address, coords)
        main_file = park_dir / f"{sanitized_name}.md"
        with open(main_file, 'w') as f:
            f.write(main_report)

        # Generate user data
        user_data = create_user_data(park_name, address, coords, coasters)
        user_file = park_dir / "user-data.md"
        with open(user_file, 'w') as f:
            f.write(user_data)

        created_count += 1
        print(f"Created: {park_name} ({len(coasters)} coasters)")

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Parks created: {created_count}")
    print(f"  Total geocoded parks: {len(geocoded_parks)}")
    print(f"  Parks with coaster data: {len(parks_coasters)}")
    print(f"{'='*60}")

    # Report any parks with coasters but no geocoding
    missing_geocodes = set(parks_coasters.keys()) - set(geocoded_parks.keys())
    if missing_geocodes:
        print(f"\nWarning: {len(missing_geocodes)} parks have coasters but no geocoding:")
        for park in sorted(missing_geocodes):
            print(f"  - {park}")


if __name__ == "__main__":
    generate_all_park_files()
