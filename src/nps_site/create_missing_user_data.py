#!/usr/bin/env python3
"""
Create missing user-data.md files for sites that have ambers-data.md but no user-data.md.
"""

import os
from pathlib import Path


def parse_ambers_data(content: str) -> dict:
    """Parse ambers-data.md content to extract structured data."""
    data = {
        'visitor_center': '',
        'address': '',
        'hours': ''
    }

    lines = content.strip().split('\n')
    for line in lines:
        if line.startswith('**Visitor Center:**'):
            data['visitor_center'] = line.replace('**Visitor Center:**', '').strip()
        elif line.startswith('**Address:**'):
            data['address'] = line.replace('**Address:**', '').strip()
        elif line.startswith('**Hours:**'):
            data['hours'] = line.replace('**Hours:**', '').strip()

    return data


def create_user_data_file(site_dir: Path, site_name: str, ambers_data: dict):
    """Create a user-data.md file for a site."""
    # Try to find the main report file
    report_files = list(site_dir.glob("*.md"))
    report_files = [f for f in report_files if f.name != "ambers-data.md"]

    report_link = ""
    if report_files:
        # URL encode the filename
        report_filename = report_files[0].name
        report_link = f"[View Full Research Report]({report_filename.replace(' ', '%20')})\n\n"

    hours = ambers_data['hours'] if ambers_data['hours'] else "Hours not available"

    content = f"""# {site_name}

{report_link}- [ ] Visited

## Cancellation Stamps

- [ ] {ambers_data['visitor_center']} ({ambers_data['address']})

## Key Activities

*To be researched and populated*

## Hidden Gems

*To be researched and populated*

## Also Nearby

*To be researched and populated*

## Review / Personal Notes



## Amber's Data (from spreadsheet)

**Visitor Center:** {ambers_data['visitor_center']}

**Address:** {ambers_data['address']}

**Hours:** {hours}
"""

    user_data_file = site_dir / "user-data.md"
    with open(user_data_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✓ Created user-data.md for {site_name}")


def main():
    nps_dir = Path("/workspace/2-Enhanced Data/NPS")

    if not nps_dir.exists():
        print(f"ERROR: {nps_dir} does not exist")
        return

    print("=" * 70)
    print("CREATING MISSING USER-DATA.MD FILES")
    print("=" * 70)

    created_count = 0

    # Find all site directories with ambers-data.md but no user-data.md
    for site_dir in sorted(nps_dir.iterdir()):
        if not site_dir.is_dir():
            continue

        ambers_file = site_dir / "ambers-data.md"
        user_data_file = site_dir / "user-data.md"

        if ambers_file.exists() and not user_data_file.exists():
            print(f"\nProcessing: {site_dir.name}")

            try:
                # Read Amber's data
                with open(ambers_file, 'r', encoding='utf-8') as f:
                    ambers_content = f.read()

                ambers_data = parse_ambers_data(ambers_content)

                # Create user-data.md
                create_user_data_file(site_dir, site_dir.name, ambers_data)
                created_count += 1

            except Exception as e:
                print(f"✗ Error creating user-data.md for {site_dir.name}: {e}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"✓ user-data.md files created: {created_count}")


if __name__ == "__main__":
    main()
