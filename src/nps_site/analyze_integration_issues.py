#!/usr/bin/env python3
"""
Analyze the integration issues to understand what happened.
"""

import os
import re
from pathlib import Path


def check_user_data_has_stamp_info(user_file: Path) -> bool:
    """Check if user-data.md has any cancellation stamp information."""
    try:
        content = user_file.read_text(encoding='utf-8')

        # Look for Cancellation Stamps section with content
        stamps_section = re.search(r'## Cancellation Stamps\s*\n\s*\n(.+?)(?=\n##|\Z)', content, re.DOTALL)

        if stamps_section:
            section_content = stamps_section.group(1).strip()
            # Check if there's actual content (not just empty or placeholder)
            if section_content and len(section_content) > 10:
                return True

        return False
    except Exception:
        return False


def analyze_sites():
    """Analyze sites to understand the integration results."""
    nps_base_dir = Path("/workspace/2-Enhanced Data/NPS")

    issues_from_script = [
        "Aniakchak NM and PRES",
        "Arches NP",
        "Arkansas Post N MEM",
        "Assateague Island NS",
        "Badlands NP",
        "Belmont-Paul Women's Equality NM",
        "Blackstone River Valley NHP",
        "Blackwell School NHS",
        "Cedar Creek and Belle Grove NHP",
        "Chamizal N MEM",
        "Colonial NHP",
        "Coltsville NHP",
        "Devils Tower NM",
        "Ebey's Landing NH RES",
        "Eisenhower NHS",
        "Eugene O'Neill NHS",
        "Ford's Theatre NHS",
        "Fort Larned NHS",
        "Fort Monroe NM",
        "Fossil Butte NM"
    ]

    print("\nAnalyzing sample of sites that reported issues:\n")
    print("="*80)

    for site_name in issues_from_script[:10]:
        site_dir = nps_base_dir / site_name
        user_file = site_dir / "user-data.md"

        if not user_file.exists():
            print(f"\n{site_name}:")
            print("  ❌ user-data.md does not exist")
            continue

        has_stamps = check_user_data_has_stamp_info(user_file)

        print(f"\n{site_name}:")
        if has_stamps:
            print("  ✓ user-data.md HAS cancellation stamp information")
            print("  → Issue was likely due to ambers-data.md having incomplete data")
        else:
            print("  ⚠️  user-data.md MISSING cancellation stamp information")
            print("  → This is a real data gap")


if __name__ == '__main__':
    analyze_sites()
