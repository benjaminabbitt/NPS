#!/usr/bin/env python3
"""
Split World's Largest attractions into individual files similar to NPS sites.

Reads World's Largest.md and creates:
- Directory for each attraction: /workspace/2-Enhanced Data/World's Largest/[Attraction Name]/
- Main report: [Attraction Name].md
- User data: user-data.md
"""

import os
import re
from pathlib import Path
from urllib.parse import quote


def sanitize_directory_name(name: str) -> str:
    """Sanitize attraction name for directory/file name."""
    # Remove special characters, replace with underscores
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Remove leading/trailing whitespace and dots
    name = name.strip('. ')
    # Replace multiple spaces/underscores with single underscore
    name = re.sub(r'[\s_]+', ' ', name)
    return name


def extract_gps_from_address(address_block: str) -> tuple[str, str]:
    """Extract GPS coordinates from address block if present."""
    gps_match = re.search(r'\*\*GPS:\*\*\s*([\d.]+°?\s*[NS],?\s*[\d.]+°?\s*[WE])', address_block)
    if gps_match:
        return gps_match.group(1), gps_match.group(0)

    # Try inline format [lat, lon]
    inline_match = re.search(r'\[([\d.-]+),\s*([\d.-]+)\]', address_block)
    if inline_match:
        lat, lon = inline_match.groups()
        lat_f = float(lat)
        lon_f = float(lon)
        lat_dir = 'N' if lat_f >= 0 else 'S'
        lon_dir = 'E' if lon_f >= 0 else 'W'
        gps_str = f"{abs(lat_f)}° {lat_dir}, {abs(lon_f)}° {lon_dir}"
        return gps_str, inline_match.group(0)

    return "", ""


def is_section_header(title: str) -> bool:
    """Check if this is a section header rather than an attraction."""
    section_keywords = [
        'NATURAL FORMATIONS',
        'MAJOR MONUMENTS',
        'QUIRKY ROADSIDE',
        'BALLS OF THINGS',
        'FOOD ITEMS',
        'ANIMAL STATUES',
        'STATUES',
        'SPORTS EQUIPMENT',
        'MUSICAL INSTRUMENTS',
        'VEHICLES & EQUIPMENT',
        'ADDITIONAL NOTABLE',
        'SEASONAL CONSIDERATIONS',
        'VERIFICATION STATUS',
        'REGIONAL ITINERARIES',
        'PRACTICAL TIPS',
        'CONTACT INFORMATION',
        'TRIP PLANNING'
    ]
    return any(keyword in title.upper() for keyword in section_keywords)


def parse_attractions(content: str) -> list[dict]:
    """Parse attractions from markdown content."""
    attractions = []

    # Split content by lines to process hierarchically
    lines = content.split('\n')

    i = 0
    while i < len(lines):
        line = lines[i]

        # Look for #### headers (individual attractions within subsections)
        if line.startswith('#### '):
            title_line = line[5:].strip()

            # Extract title and markers
            markers = []
            if '✓' in title_line:
                markers.append('✓')
            for marker in ['[SELF-DECLARED]', '[CONTESTED]', '[CLOSED]', '[DETERIORATED]', '[LIMITED ACCESS]']:
                if marker in title_line:
                    markers.append(marker)

            # Clean title
            title = title_line
            for marker in markers + ['✓']:
                title = title.replace(marker, '')
            title = title.strip()

            # Skip if section header
            if is_section_header(title):
                i += 1
                continue

            # Collect content until next #### or ### or ---
            content_lines = []
            i += 1
            while i < len(lines):
                if lines[i].startswith('####') or lines[i].startswith('###') or lines[i].strip() == '---':
                    break
                content_lines.append(lines[i])
                i += 1

            full_content = '\n'.join(content_lines).strip()

            # Skip if no substantial content
            if len(full_content) < 50:
                continue

            # Extract key fields
            what_makes_match = re.search(r'\*\*What Makes It World\'s Largest:\*\*\s*(.+?)(?=\n\*\*|\n\n|$)', full_content, re.DOTALL)
            what_makes = what_makes_match.group(1).strip() if what_makes_match else ""

            address_match = re.search(r'\*\*Address:\*\*\s*(.+?)(?=\n\*\*|\n\n|$)', full_content, re.DOTALL)
            address = address_match.group(1).strip() if address_match else ""

            location_match = re.search(r'\*\*Location:\*\*\s*(.+?)(?=\n\*\*|\n\n|$)', full_content, re.DOTALL)
            location = location_match.group(1).strip() if location_match else ""

            hours_match = re.search(r'\*\*Hours:\*\*\s*(.+?)(?=\n\*\*|\n\n|$)', full_content, re.DOTALL)
            hours = hours_match.group(1).strip() if hours_match else ""

            fees_match = re.search(r'\*\*Fees:\*\*\s*(.+?)(?=\n\*\*|\n\n|$)', full_content, re.DOTALL)
            fees = fees_match.group(1).strip() if fees_match else ""

            # Extract GPS if present
            gps_coords, _ = extract_gps_from_address(full_content)

            attractions.append({
                'title': title,
                'markers': markers,
                'what_makes': what_makes,
                'address': address or location,
                'gps': gps_coords,
                'hours': hours,
                'fees': fees,
                'full_content': full_content
            })

        # Look for ### headers (top-level attractions)
        elif line.startswith('### '):
            title_line = line[4:].strip()

            # Skip section headers
            if is_section_header(title_line):
                i += 1
                continue

            # Extract title and markers
            markers = []
            if '✓' in title_line:
                markers.append('✓')
            for marker in ['[SELF-DECLARED]', '[CONTESTED]', '[CLOSED]', '[DETERIORATED]', '[LIMITED ACCESS]']:
                if marker in title_line:
                    markers.append(marker)

            # Clean title
            title = title_line
            for marker in markers + ['✓']:
                title = title.replace(marker, '')
            title = title.strip()

            # Collect content until next ### or ---
            content_lines = []
            i += 1
            while i < len(lines):
                # Stop at next ### header (unless it's a #### subheader)
                if lines[i].startswith('###') and not lines[i].startswith('####'):
                    break
                if lines[i].strip() == '---' and (i + 1 >= len(lines) or lines[i + 1].startswith('##')):
                    break
                content_lines.append(lines[i])
                i += 1

            full_content = '\n'.join(content_lines).strip()

            # Skip if no substantial content or has #### subheaders (means it's a category)
            if len(full_content) < 50 or '####' in full_content:
                continue

            # Extract key fields
            what_makes_match = re.search(r'\*\*What Makes It World\'s Largest:\*\*\s*(.+?)(?=\n\*\*|\n\n|$)', full_content, re.DOTALL)
            what_makes = what_makes_match.group(1).strip() if what_makes_match else ""

            address_match = re.search(r'\*\*Address:\*\*\s*(.+?)(?=\n\*\*|\n\n|$)', full_content, re.DOTALL)
            address = address_match.group(1).strip() if address_match else ""

            location_match = re.search(r'\*\*Location:\*\*\s*(.+?)(?=\n\*\*|\n\n|$)', full_content, re.DOTALL)
            location = location_match.group(1).strip() if location_match else ""

            hours_match = re.search(r'\*\*Hours:\*\*\s*(.+?)(?=\n\*\*|\n\n|$)', full_content, re.DOTALL)
            hours = hours_match.group(1).strip() if hours_match else ""

            fees_match = re.search(r'\*\*Fees:\*\*\s*(.+?)(?=\n\*\*|\n\n|$)', full_content, re.DOTALL)
            fees = fees_match.group(1).strip() if fees_match else ""

            # Extract GPS if present
            gps_coords, _ = extract_gps_from_address(full_content)

            attractions.append({
                'title': title,
                'markers': markers,
                'what_makes': what_makes,
                'address': address or location,
                'gps': gps_coords,
                'hours': hours,
                'fees': fees,
                'full_content': full_content
            })
        else:
            i += 1

    return attractions


def create_main_report(attraction: dict, file_path: Path):
    """Create main report file for attraction."""
    markers_str = ' '.join(attraction['markers'])

    content = f"""# {attraction['title']} {markers_str}

{attraction['full_content']}
"""

    file_path.write_text(content)


def create_user_data(attraction: dict, file_path: Path, main_report_name: str):
    """Create user-data.md file for attraction."""
    # Create URL-encoded link to main report
    encoded_name = quote(main_report_name)

    # Format location info
    location_info = attraction['address']
    if attraction['gps']:
        if location_info:
            location_info += f"\n\nGPS: {attraction['gps']}"
        else:
            location_info = f"GPS: {attraction['gps']}"

    content = f"""# {attraction['title']}

[View Full Details]({encoded_name})

- [ ] Visited

## What Makes It World's Largest

{attraction['what_makes'] if attraction['what_makes'] else 'See main report for details'}

## Location

{location_info if location_info else 'See main report for details'}

## Hours

{attraction['hours'] if attraction['hours'] else 'See main report for details'}

## Fees

{attraction['fees'] if attraction['fees'] else 'See main report for details'}

## Review / Personal Notes

"""

    file_path.write_text(content)


def main():
    # Read source file
    source_file = Path('/workspace/2-Enhanced Data/World\'s Largest/World\'s Largest.md')
    base_dir = Path('/workspace/2-Enhanced Data/World\'s Largest')

    if not source_file.exists():
        print(f"ERROR: Source file not found: {source_file}")
        return

    content = source_file.read_text()

    # Parse attractions
    print("Parsing attractions...")
    attractions = parse_attractions(content)
    print(f"Found {len(attractions)} attractions to process")

    # Process each attraction
    created_count = 0
    skipped_count = 0
    errors = []

    for attraction in attractions:
        try:
            # Create sanitized directory name
            dir_name = sanitize_directory_name(attraction['title'])
            attr_dir = base_dir / dir_name

            # Create directory
            attr_dir.mkdir(parents=True, exist_ok=True)

            # Create main report file
            main_report_name = f"{dir_name}.md"
            main_report_path = attr_dir / main_report_name
            create_main_report(attraction, main_report_path)

            # Create user data file
            user_data_path = attr_dir / "user-data.md"
            create_user_data(attraction, user_data_path, main_report_name)

            created_count += 1
            print(f"✓ Created: {dir_name}")

        except Exception as e:
            skipped_count += 1
            error_msg = f"ERROR processing '{attraction['title']}': {str(e)}"
            errors.append(error_msg)
            print(error_msg)

    # Print summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total attractions processed: {len(attractions)}")
    print(f"Successfully created: {created_count}")
    print(f"Skipped/Errors: {skipped_count}")

    if errors:
        print("\nErrors encountered:")
        for error in errors:
            print(f"  - {error}")

    print(f"\nDirectory structure created at: {base_dir}")


if __name__ == '__main__':
    main()
