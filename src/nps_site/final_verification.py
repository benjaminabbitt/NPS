#!/usr/bin/env python3
"""
Final verification of the Amber's data integration.
"""

import os
import re
from pathlib import Path


def main():
    nps_base_dir = Path("/workspace/2-Enhanced Data/NPS")

    # Get all site directories
    site_dirs = [d for d in nps_base_dir.iterdir() if d.is_dir()]

    stats = {
        'total_sites': len(site_dirs),
        'has_user_data': 0,
        'has_ambers_data': 0,
        'has_ambers_section': 0,
        'has_stamp_info': 0,
        'missing_stamp_info': 0
    }

    sites_missing_stamps = []

    for site_dir in site_dirs:
        user_file = site_dir / "user-data.md"
        ambers_file = site_dir / "ambers-data.md"

        # Check for files
        if user_file.exists():
            stats['has_user_data'] += 1

        if ambers_file.exists():
            stats['has_ambers_data'] += 1

        # Check for Amber's Data section in user-data.md
        if user_file.exists():
            content = user_file.read_text(encoding='utf-8')

            if "## Amber's Data" in content:
                stats['has_ambers_section'] += 1

            # Check for stamp information
            stamps_section = re.search(
                r'## Cancellation Stamps\s*\n\s*\n(.+?)(?=\n##|\Z)',
                content,
                re.DOTALL
            )

            if stamps_section:
                section_content = stamps_section.group(1).strip()
                if section_content and len(section_content) > 10:
                    stats['has_stamp_info'] += 1
                else:
                    stats['missing_stamp_info'] += 1
                    sites_missing_stamps.append(site_dir.name)
            else:
                stats['missing_stamp_info'] += 1
                sites_missing_stamps.append(site_dir.name)

    print("\n" + "="*80)
    print("FINAL VERIFICATION RESULTS")
    print("="*80)
    print(f"\nTotal NPS site directories: {stats['total_sites']}")
    print(f"Sites with user-data.md: {stats['has_user_data']}")
    print(f"\n✓ Remaining ambers-data.md files: {stats['has_ambers_data']} (should be 0)")
    print(f"✓ Remaining Amber's Data sections in user-data.md: {stats['has_ambers_section']} (should be 0)")
    print(f"\nSites with cancellation stamp information: {stats['has_stamp_info']}")
    print(f"Sites missing cancellation stamp information: {stats['missing_stamp_info']}")

    if stats['missing_stamp_info'] > 0:
        print(f"\nSites missing stamp information ({len(sites_missing_stamps)}):")
        for i, site in enumerate(sorted(sites_missing_stamps)[:20], 1):
            print(f"  {i}. {site}")
        if len(sites_missing_stamps) > 20:
            print(f"  ... and {len(sites_missing_stamps) - 20} more")

    print("\n" + "="*80)
    print("\nSUMMARY:")
    if stats['has_ambers_data'] == 0 and stats['has_ambers_section'] == 0:
        print("✓ SUCCESS: All ambers-data.md files deleted")
        print("✓ SUCCESS: All Amber's Data sections removed from user-data.md files")
    else:
        print("⚠️  INCOMPLETE: Some cleanup items remain")

    print("="*80 + "\n")


if __name__ == '__main__':
    main()
