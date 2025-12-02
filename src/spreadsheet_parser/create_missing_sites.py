#!/usr/bin/env python3
"""
Create missing NPS site directories and user-data.md files.

This script identifies sites from the CSV that don't have directories
or user-data.md files and creates them.
"""

import csv
from pathlib import Path

from name_mapping import (
    ENHANCED_DATA_PATH,
    get_directory_name,
    get_directory_path,
    directory_exists,
    user_data_exists,
    expand_abbreviation,
    normalize_name,
)

# Path to CSV
CSV_PATH = Path("/workspace/1-Raw Input Data/NPS/Untitled spreadsheet - US Parks.csv")


def create_user_data_template(site_name: str, dir_name: str) -> str:
    """Create the user-data.md template content."""
    # URL-encode the filename for the link
    md_filename = f"{dir_name}.md".replace(" ", "%20")

    return f"""# {dir_name}

[View Full Research Report]({md_filename})

- [ ] Visited

## Cancellation Stamps

*To be researched and populated*

## Key Activities

*To be researched and populated*

## Hidden Gems

*To be researched and populated*

## Also Nearby

*To be researched and populated*

## Review / Personal Notes

"""


def create_site_report_template(site_name: str, dir_name: str) -> str:
    """Create the main site report template."""
    expanded_name = expand_abbreviation(dir_name)

    return f"""# {expanded_name}

## Cancellation Stamp Locations

*This section requires comprehensive research. See CLAUDE.md for research instructions.*

**Note:** Call to confirm current stamp locations before visiting.

## Key Activities

*This section requires comprehensive research. See CLAUDE.md for research instructions.*

## Hidden Gems

*This section requires comprehensive research. See CLAUDE.md for research instructions.*

## Also Nearby

*This section requires comprehensive research. See CLAUDE.md for research instructions.*

---

**Total Recommended Time:** *To be determined through research*
"""


def get_missing_sites() -> list[dict]:
    """
    Read CSV and identify sites missing directories or user-data.md files.

    Returns list of dicts with site info.
    """
    missing = []

    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header

        for row_num, row in enumerate(reader, start=2):
            if len(row) < 5 or not row[4] or row[4].strip() == '':
                continue

            csv_name = row[4].strip()
            if not csv_name:
                continue

            # Skip bad data entries
            normalized = normalize_name(csv_name)
            if ";" in normalized and "memorial parks" in normalized:
                # Skip malformed "National Mall & Memorial Parks; Northeast" entry
                continue

            dir_name = get_directory_name(csv_name)
            dir_path = get_directory_path(csv_name)

            dir_missing = not directory_exists(csv_name)
            user_data_missing = not user_data_exists(csv_name)

            if dir_missing or user_data_missing:
                missing.append({
                    'csv_name': csv_name,
                    'dir_name': dir_name,
                    'dir_path': dir_path,
                    'dir_missing': dir_missing,
                    'user_data_missing': user_data_missing,
                })

    return missing


def create_missing_sites(dry_run: bool = False) -> dict:
    """
    Create missing directories and user-data.md files.

    Args:
        dry_run: If True, only report what would be created

    Returns:
        Dict with counts of created items
    """
    missing = get_missing_sites()

    results = {
        'dirs_created': 0,
        'user_data_created': 0,
        'reports_created': 0,
        'errors': [],
    }

    for site in missing:
        csv_name = site['csv_name']
        dir_name = site['dir_name']
        dir_path = site['dir_path']

        print(f"\nProcessing: {csv_name}")
        print(f"  -> Directory: {dir_name}")

        try:
            # Create directory if missing
            if site['dir_missing']:
                if dry_run:
                    print(f"  [DRY RUN] Would create directory: {dir_path}")
                else:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    print(f"  Created directory: {dir_path}")
                results['dirs_created'] += 1

            # Create user-data.md if missing
            user_data_path = dir_path / "user-data.md"
            if site['user_data_missing'] or site['dir_missing']:
                if dry_run:
                    print(f"  [DRY RUN] Would create: {user_data_path}")
                else:
                    content = create_user_data_template(csv_name, dir_name)
                    user_data_path.write_text(content, encoding='utf-8')
                    print(f"  Created: user-data.md")
                results['user_data_created'] += 1

            # Create main report if missing
            report_path = dir_path / f"{dir_name}.md"
            if site['dir_missing'] or not report_path.exists():
                if dry_run:
                    print(f"  [DRY RUN] Would create: {report_path}")
                else:
                    content = create_site_report_template(csv_name, dir_name)
                    report_path.write_text(content, encoding='utf-8')
                    print(f"  Created: {dir_name}.md")
                results['reports_created'] += 1

        except Exception as e:
            error_msg = f"Error processing {csv_name}: {e}"
            print(f"  ERROR: {e}")
            results['errors'].append(error_msg)

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Create missing NPS site files")
    parser.add_argument('--dry-run', action='store_true',
                        help="Only show what would be created, don't actually create")
    parser.add_argument('--list-only', action='store_true',
                        help="Only list missing sites, don't create anything")
    args = parser.parse_args()

    print("=" * 60)
    print("NPS Missing Sites Creator")
    print("=" * 60)

    if args.list_only:
        missing = get_missing_sites()
        print(f"\nFound {len(missing)} sites with missing files:\n")

        # Group by issue type
        dir_missing = [s for s in missing if s['dir_missing']]
        user_data_only = [s for s in missing if not s['dir_missing'] and s['user_data_missing']]

        if dir_missing:
            print(f"\n## Missing Directories ({len(dir_missing)}):\n")
            for site in dir_missing:
                print(f"  - {site['csv_name']}")
                print(f"    -> Would create: {site['dir_name']}/")

        if user_data_only:
            print(f"\n## Missing user-data.md Only ({len(user_data_only)}):\n")
            for site in user_data_only:
                print(f"  - {site['csv_name']}")
                print(f"    -> In: {site['dir_name']}/")

        return

    results = create_missing_sites(dry_run=args.dry_run)

    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    print(f"  Directories created: {results['dirs_created']}")
    print(f"  user-data.md created: {results['user_data_created']}")
    print(f"  Site reports created: {results['reports_created']}")

    if results['errors']:
        print(f"\n  Errors ({len(results['errors'])}):")
        for error in results['errors']:
            print(f"    - {error}")


if __name__ == "__main__":
    main()
