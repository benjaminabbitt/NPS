#!/usr/bin/env python3
"""
Integrate Amber's data into user-data.md files and remove hash codes.

This script:
1. Finds all ambers-data.md files in the NPS directory
2. Integrates the data into corresponding user-data.md files
3. Deletes ambers-data.md files after successful integration
4. Removes hash codes from all markdown files
"""

import os
import re
from pathlib import Path
from typing import Dict, Tuple, Optional


def parse_ambers_data(content: str) -> Dict[str, str]:
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


def find_ambers_section(content: str) -> Tuple[bool, int, int]:
    """
    Find if Amber's Data section exists in user-data.md.

    Returns:
        (exists, start_index, end_index)
    """
    lines = content.split('\n')
    start_idx = -1
    end_idx = -1

    for i, line in enumerate(lines):
        if line.strip() == "## Amber's Data (from spreadsheet)":
            start_idx = i
            # Find the end (next ## section or end of file)
            for j in range(i + 1, len(lines)):
                if lines[j].startswith('## ') and j > i:
                    end_idx = j
                    break
            if end_idx == -1:
                end_idx = len(lines)
            break

    exists = start_idx != -1
    return exists, start_idx, end_idx


def create_ambers_section(data: Dict[str, str]) -> str:
    """Create the Amber's Data section content."""
    hours = data['hours'] if data['hours'] else "Hours not available"

    section = f"""## Amber's Data (from spreadsheet)

**Visitor Center:** {data['visitor_center']}

**Address:** {data['address']}

**Hours:** {hours}
"""
    return section


def integrate_ambers_data(site_dir: Path) -> bool:
    """
    Integrate ambers-data.md into user-data.md for a single site.

    Returns:
        True if successful, False otherwise
    """
    ambers_file = site_dir / "ambers-data.md"
    user_data_file = site_dir / "user-data.md"

    if not ambers_file.exists():
        return False

    if not user_data_file.exists():
        print(f"WARNING: {user_data_file} not found, skipping {site_dir.name}")
        return False

    # Read Amber's data
    with open(ambers_file, 'r', encoding='utf-8') as f:
        ambers_content = f.read()

    ambers_data = parse_ambers_data(ambers_content)

    # Read user-data.md
    with open(user_data_file, 'r', encoding='utf-8') as f:
        user_content = f.read()

    # Check if section exists
    exists, start_idx, end_idx = find_ambers_section(user_content)

    # Create new section
    new_section = create_ambers_section(ambers_data)

    lines = user_content.split('\n')

    if exists:
        # Replace existing section
        lines = lines[:start_idx] + new_section.strip().split('\n') + lines[end_idx:]
    else:
        # Add section at the end
        # Make sure there's a blank line before the new section
        if lines and lines[-1].strip():
            lines.append('')
        lines.extend(new_section.strip().split('\n'))
        lines.append('')  # Add trailing newline

    # Write updated content
    updated_content = '\n'.join(lines)
    with open(user_data_file, 'w', encoding='utf-8') as f:
        f.write(updated_content)

    return True


def remove_hash_codes_from_file(file_path: Path) -> int:
    """
    Remove hash codes in square brackets from a markdown file.

    Pattern: space + [6-character hex string]
    Example: " [abc123]"

    Returns:
        Number of hash codes removed
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern: space followed by [6 hex characters]
    pattern = r' \[[0-9a-f]{6}\]'

    # Count matches
    matches = re.findall(pattern, content)
    count = len(matches)

    if count > 0:
        # Remove matches
        updated_content = re.sub(pattern, '', content)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)

    return count


def main():
    nps_dir = Path("/workspace/2-Enhanced Data/NPS")

    if not nps_dir.exists():
        print(f"ERROR: {nps_dir} does not exist")
        return

    print("=" * 70)
    print("PART 1: INTEGRATING AMBER'S DATA")
    print("=" * 70)

    # Track statistics
    sites_processed = 0
    sites_with_ambers_data = 0
    ambers_files_deleted = 0
    errors = []

    # Find all site directories with ambers-data.md
    for site_dir in sorted(nps_dir.iterdir()):
        if not site_dir.is_dir():
            continue

        ambers_file = site_dir / "ambers-data.md"

        if ambers_file.exists():
            sites_with_ambers_data += 1
            print(f"\nProcessing: {site_dir.name}")

            try:
                # Integrate data
                if integrate_ambers_data(site_dir):
                    sites_processed += 1
                    print(f"  ✓ Integrated data into user-data.md")

                    # Delete ambers-data.md
                    ambers_file.unlink()
                    ambers_files_deleted += 1
                    print(f"  ✓ Deleted ambers-data.md")
                else:
                    errors.append(f"{site_dir.name}: Integration failed")
                    print(f"  ✗ Integration failed")

            except Exception as e:
                errors.append(f"{site_dir.name}: {str(e)}")
                print(f"  ✗ Error: {e}")

    print("\n" + "=" * 70)
    print("PART 1 SUMMARY")
    print("=" * 70)
    print(f"Sites with ambers-data.md found: {sites_with_ambers_data}")
    print(f"Sites successfully processed: {sites_processed}")
    print(f"ambers-data.md files deleted: {ambers_files_deleted}")

    if errors:
        print(f"\nErrors encountered: {len(errors)}")
        for error in errors:
            print(f"  - {error}")

    print("\n" + "=" * 70)
    print("PART 2: REMOVING HASH CODES")
    print("=" * 70)

    # Track statistics
    files_with_hash_codes = 0
    total_hash_codes_removed = 0
    files_processed_for_hashes = 0

    # Find all markdown files in NPS directory
    for site_dir in sorted(nps_dir.iterdir()):
        if not site_dir.is_dir():
            continue

        for md_file in site_dir.glob("*.md"):
            files_processed_for_hashes += 1

            count = remove_hash_codes_from_file(md_file)

            if count > 0:
                files_with_hash_codes += 1
                total_hash_codes_removed += count
                print(f"  {md_file.relative_to(nps_dir)}: removed {count} hash code(s)")

    print("\n" + "=" * 70)
    print("PART 2 SUMMARY")
    print("=" * 70)
    print(f"Markdown files processed: {files_processed_for_hashes}")
    print(f"Files with hash codes removed: {files_with_hash_codes}")
    print(f"Total hash codes removed: {total_hash_codes_removed}")

    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"✓ Sites with Amber's data integrated: {sites_processed}")
    print(f"✓ ambers-data.md files deleted: {ambers_files_deleted}")
    print(f"✓ Files with hash codes removed: {files_with_hash_codes}")
    print(f"✓ Total hash codes removed: {total_hash_codes_removed}")

    if errors:
        print(f"\n⚠ Errors encountered: {len(errors)}")
    else:
        print(f"\n✓ No errors encountered")


if __name__ == "__main__":
    main()
