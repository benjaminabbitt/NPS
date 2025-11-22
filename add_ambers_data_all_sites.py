#!/usr/bin/env python3
"""
Add Amber's Data sections to all remaining NPS sites
"""
import csv
import re
from pathlib import Path

def format_hours(csv_row):
    """Format operating hours from CSV"""
    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    hours_lines = []

    for day in days:
        hours = csv_row.get(day, '').strip()
        if hours:
            hours_lines.append(f"- **{day}:** {hours}")

    return '\n'.join(hours_lines) if hours_lines else None

def site_has_ambers_data(site_name):
    """Check if site already has Amber's Data section"""
    main_md_file = Path(f'2-Enhanced Data/NPS/{site_name}/{site_name}.md')

    if not main_md_file.exists():
        return False

    content = main_md_file.read_text()
    return "## Amber's Data" in content

def add_ambers_data_to_main_md(site_name, csv_row):
    """Add Amber's Data section to main markdown file"""
    main_md_file = Path(f'2-Enhanced Data/NPS/{site_name}/{site_name}.md')

    if not main_md_file.exists():
        return False

    content = main_md_file.read_text()

    # Build the Amber's Data section
    ambers_section = "\n\n## Amber's Data\n\n"
    ambers_section += "*This section preserves the original data from the source spreadsheet.*\n\n"

    # Main address
    address = csv_row.get('Address', '').strip()
    city = csv_row.get('City', '').strip()
    state = csv_row.get('State', '').strip()
    zip_code = csv_row.get('Zip', '').strip()

    if address:
        ambers_section += f"**Main Address:** {address}"
        if city:
            ambers_section += f", {city}"
        if state:
            ambers_section += f", {state}"
        if zip_code:
            ambers_section += f" {zip_code}"
        ambers_section += "\n\n"

    # Operating hours
    hours = format_hours(csv_row)
    if hours:
        ambers_section += "**Operating Hours (from source):**\n"
        ambers_section += hours + "\n\n"

    # Visitor center info
    vc_location = csv_row.get('Visitor Center Location', '').strip()
    vc_address = csv_row.get('Visitor Center Address', '').strip()

    if vc_location or vc_address:
        ambers_section += "**Visitor Center (from source):**\n"
        if vc_location:
            ambers_section += f"- **Name:** {vc_location}\n"
        if vc_address:
            ambers_section += f"- **Address:** {vc_address}\n"

    # Append to the end of the file
    content += ambers_section

    main_md_file.write_text(content)
    return True

def main():
    print("="*70)
    print("Adding Amber's Data Sections to All Remaining Sites")
    print("="*70)

    # Read the CSV file
    csv_file = Path('1-Raw Input Data/NPS/Untitled spreadsheet - US Parks.csv')

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        csv_data = {row['National Park']: row for row in reader}

    # Get all sites
    base_path = Path('2-Enhanced Data/NPS')
    all_sites = [d.name for d in base_path.iterdir() if d.is_dir()]

    print(f"\nFound {len(all_sites)} sites")
    print(f"CSV file has {len(csv_data)} entries")

    # Process each site
    print("\nProcessing...")

    added_count = 0
    already_has_count = 0
    no_csv_data_count = 0

    for i, site in enumerate(sorted(all_sites), 1):
        if i % 50 == 0:
            print(f"  Progress: {i}/{len(all_sites)}")

        # Check if already has Amber's Data
        if site_has_ambers_data(site):
            already_has_count += 1
            continue

        # Find matching CSV row
        csv_row = csv_data.get(site)

        if not csv_row:
            no_csv_data_count += 1
            continue

        # Add Amber's Data section
        if add_ambers_data_to_main_md(site, csv_row):
            added_count += 1

    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Total sites: {len(all_sites)}")
    print(f"Amber's Data sections added: {added_count}")
    print(f"Sites that already had Amber's Data: {already_has_count}")
    print(f"Sites without matching CSV data: {no_csv_data_count}")
    print(f"\n✓ Complete!")

if __name__ == '__main__':
    main()
