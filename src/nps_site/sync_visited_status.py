#!/usr/bin/env python3
"""
Sync visited status from Amber's spreadsheet to NPS site markdown files.

Reads the CSV file and marks sites as visited in the User Data section
if they have an "X" in the Completed column.
"""
import csv
import re
from pathlib import Path


def normalize_site_name(name: str) -> str:
    """Normalize site name for directory matching."""
    # Remove extra spaces
    name = ' '.join(name.split())
    return name.strip()


def mark_site_as_visited(site_file: Path) -> bool:
    """Mark a site as visited in the User Data section."""
    content = site_file.read_text(encoding='utf-8')

    # Check if already marked as visited
    if re.search(r'-\s*\[x\]\s*Visited', content, re.IGNORECASE):
        return False  # Already visited

    # Mark as visited
    new_content = re.sub(
        r'(-\s*\[)\s(\]\s*Visited)',
        r'\1x\2',
        content,
        flags=re.IGNORECASE
    )

    if new_content != content:
        site_file.write_text(new_content, encoding='utf-8')
        return True

    return False


def main():
    """Sync visited status from CSV to markdown files."""
    csv_path = Path('1-Raw Input Data/NPS/Untitled spreadsheet - US Parks.csv')
    nps_dir = Path('2-Enhanced Data/NPS')

    if not csv_path.exists():
        print(f"Error: CSV file not found at {csv_path}")
        return

    if not nps_dir.exists():
        print(f"Error: NPS directory not found at {nps_dir}")
        return

    # Read CSV and find completed sites
    completed_sites = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Check if Completed column has 'X'
            if row.get('Completed', '').strip().upper() == 'X':
                site_name = row.get('National Park', '').strip()
                if site_name:
                    completed_sites.append(normalize_site_name(site_name))

    print(f"Found {len(completed_sites)} completed sites in spreadsheet:\n")

    # Update markdown files
    updated_count = 0
    already_visited_count = 0
    not_found_count = 0

    for site_name in completed_sites:
        # Try to find the site directory
        site_dirs = list(nps_dir.glob(f"{site_name}"))

        if not site_dirs:
            # Try with wildcards for sites with special characters
            site_dirs = [d for d in nps_dir.iterdir()
                        if d.is_dir() and site_name.lower() in d.name.lower()]

        if site_dirs:
            site_dir = site_dirs[0]
            md_files = list(site_dir.glob('*.md'))
            main_file = None

            # Find main report file (not user-data.md)
            for f in md_files:
                if 'user-data' not in f.name.lower():
                    main_file = f
                    break

            if main_file and main_file.exists():
                was_updated = mark_site_as_visited(main_file)
                if was_updated:
                    print(f"  ✅ Updated: {site_name}")
                    updated_count += 1
                else:
                    print(f"  ℹ️  Already visited: {site_name}")
                    already_visited_count += 1
            else:
                print(f"  ⚠️  No main file found: {site_name}")
                not_found_count += 1
        else:
            print(f"  ❌ Directory not found: {site_name}")
            not_found_count += 1

    print(f"\n" + "="*60)
    print(f"Summary:")
    print(f"  - Updated: {updated_count}")
    print(f"  - Already visited: {already_visited_count}")
    print(f"  - Not found: {not_found_count}")
    print(f"  - Total processed: {len(completed_sites)}")


if __name__ == '__main__':
    main()
