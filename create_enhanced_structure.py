#!/usr/bin/env python3
"""
Create 2-Enhanced Data directory structure for all NPS sites
"""

from pathlib import Path
import shutil

def create_enhanced_structure():
    """Create directory structure and copy site reports"""

    # Create base directory
    enhanced_dir = Path("2-Enhanced Data")
    enhanced_dir.mkdir(exist_ok=True)

    # Get all site reports
    site_reports_dir = Path("site_reports")

    if not site_reports_dir.exists():
        print(f"Error: {site_reports_dir} does not exist")
        return

    site_files = list(site_reports_dir.glob("*.md"))

    print(f"Processing {len(site_files)} site reports...")
    print("="*70)

    for i, site_file in enumerate(site_files, 1):
        # Get site name (without .md extension)
        site_name = site_file.stem

        # Create site directory
        site_dir = enhanced_dir / site_name
        site_dir.mkdir(exist_ok=True)

        # Copy site report
        dest_file = site_dir / site_file.name
        shutil.copy2(site_file, dest_file)

        # Create empty override.md
        override_file = site_dir / "override.md"
        if not override_file.exists():
            override_file.write_text("", encoding='utf-8')

        if i % 50 == 0:
            print(f"  Processed {i}/{len(site_files)} sites")

    print("="*70)
    print(f"Complete! Created {len(site_files)} site directories")
    print(f"\nStructure:")
    print(f"  2-Enhanced Data/")
    print(f"    ├── {{site_name}}/")
    print(f"    │   ├── {{site_name}}.md")
    print(f"    │   └── override.md")
    print(f"    ... ({len(site_files)} directories)")


if __name__ == '__main__':
    create_enhanced_structure()
