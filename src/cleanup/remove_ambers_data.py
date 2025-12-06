#!/usr/bin/env python3
"""
Remove "Amber's Data" sections from NPS main report files.

This script scans all NPS site directories in 2-Enhanced Data/NPS/,
finds main report files (not user-data.md), and removes any
"## Amber's Data" or "## Amber's Data (from spreadsheet)" sections.
"""

import os
import re
from pathlib import Path
from typing import Tuple, List


def remove_ambers_data_section(content: str) -> Tuple[str, bool]:
    """
    Remove the Amber's Data section from markdown content.

    Args:
        content: The markdown file content

    Returns:
        Tuple of (modified_content, was_modified)
    """
    # Pattern to match "## Amber's Data" section with optional "(from spreadsheet)"
    # Captures from the header until the next ## header or end of file
    pattern = r'## Amber\'s Data(?:\s*\(from spreadsheet\))?\s*\n(?:(?!^##\s).*\n)*'

    modified_content = re.sub(pattern, '', content, flags=re.MULTILINE)

    # Check if content was actually modified
    was_modified = content != modified_content

    return modified_content, was_modified


def process_nps_reports(base_dir: str) -> dict:
    """
    Process all NPS main report files and remove Amber's Data sections.

    Args:
        base_dir: Path to the NPS data directory

    Returns:
        Dictionary with processing statistics
    """
    stats = {
        'files_scanned': 0,
        'files_with_section': 0,
        'files_modified': 0,
        'errors': []
    }

    nps_dir = Path(base_dir)

    if not nps_dir.exists():
        stats['errors'].append(f"Directory not found: {base_dir}")
        return stats

    # Iterate through all site directories
    for site_dir in sorted(nps_dir.iterdir()):
        if not site_dir.is_dir():
            continue

        # Find main report files (not user-data.md)
        for file_path in site_dir.glob('*.md'):
            if file_path.name == 'user-data.md':
                continue

            stats['files_scanned'] += 1

            try:
                # Read the file
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check if it contains Amber's Data section
                if "## Amber's Data" in content:
                    stats['files_with_section'] += 1
                    print(f"Found Amber's Data section in: {file_path}")

                    # Remove the section
                    modified_content, was_modified = remove_ambers_data_section(content)

                    if was_modified:
                        # Write back the modified content
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(modified_content)

                        stats['files_modified'] += 1
                        print(f"  ✓ Removed section from: {file_path}")
                    else:
                        print(f"  ⚠ Pattern matched but no changes made: {file_path}")

            except Exception as e:
                error_msg = f"Error processing {file_path}: {str(e)}"
                stats['errors'].append(error_msg)
                print(f"  ✗ {error_msg}")

    return stats


def main():
    """Main execution function."""
    base_dir = '/workspace/2-Enhanced Data/NPS'

    print("=" * 70)
    print("Removing Amber's Data Sections from NPS Main Reports")
    print("=" * 70)
    print()

    stats = process_nps_reports(base_dir)

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Main report files scanned: {stats['files_scanned']}")
    print(f"Files with Amber's Data section found: {stats['files_with_section']}")
    print(f"Files successfully modified: {stats['files_modified']}")

    if stats['errors']:
        print(f"\nErrors encountered: {len(stats['errors'])}")
        for error in stats['errors']:
            print(f"  - {error}")
    else:
        print("\nNo errors encountered.")

    print("=" * 70)


if __name__ == '__main__':
    main()
