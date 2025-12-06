#!/usr/bin/env python3
"""
Integrate user-data.md into main NPS site reports.

For each NPS site:
1. Add anchor tags to list items in main report
2. Add "# User Data" section at end of main report
3. Move user-data.md content with links to anchors
4. Delete user-data.md
"""
import re
from pathlib import Path
from typing import List, Tuple


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug for anchor IDs"""
    # Remove markdown bold markers
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    # Extract just the name before any parentheses
    text = re.split(r'\s*\(', text)[0].strip()
    # Convert to lowercase and replace spaces/special chars with hyphens
    slug = text.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return slug


def add_anchors_to_list_items(content: str, section_prefix: str) -> Tuple[str, List[Tuple[str, str]]]:
    """
    Add anchor tags to markdown list items.

    Returns:
        (modified_content, [(item_name, anchor_id), ...])
    """
    anchors = []
    lines = content.split('\n')
    result = []

    for line in lines:
        # Match list items that start with - **Name**
        match = re.match(r'^(\s*-\s+)\*\*([^*]+)\*\*(.*)$', line)
        if match:
            indent, name, rest = match.groups()
            slug = slugify(name)
            anchor_id = f"{section_prefix}-{slug}"
            anchors.append((name, anchor_id))
            # Add anchor before the bold text
            new_line = f'{indent}<a id="{anchor_id}"></a>**{name}**{rest}'
            result.append(new_line)
        else:
            result.append(line)

    return '\n'.join(result), anchors


def extract_section(content: str, section_title: str) -> Tuple[str, str]:
    """
    Extract a section from markdown content.

    Returns:
        (section_content, content_without_section)
    """
    # Match section header and everything until next same-level header or end
    pattern = rf'(## {re.escape(section_title)}.*?)(?=\n## |\Z)'
    match = re.search(pattern, content, re.DOTALL)

    if match:
        section_content = match.group(1).strip()
        content_without = content[:match.start()] + content[match.end():]
        return section_content, content_without
    return '', content


def add_links_to_user_checkboxes(content: str, anchors: List[Tuple[str, str]]) -> str:
    """Add links from checkbox items to main report anchors"""
    lines = content.split('\n')
    result = []

    # Create lookup dict from item names to anchor IDs
    anchor_map = {name.strip(): anchor_id for name, anchor_id in anchors}

    for line in lines:
        # Match checkbox lines: - [ ] Name (details)
        match = re.match(r'^(\s*-\s+\[[x ]\]\s+)([^(]+)(\(.*\))?(.*)$', line, re.IGNORECASE)
        if match:
            prefix, name, details, rest = match.groups()
            name = name.strip()

            # Look for matching anchor
            anchor_id = None
            for anchor_name, aid in anchor_map.items():
                if anchor_name.lower() in name.lower() or name.lower() in anchor_name.lower():
                    anchor_id = aid
                    break

            if anchor_id:
                details = details or ''
                new_line = f'{prefix}[{name}](#{anchor_id}){details}{rest}'
                result.append(new_line)
            else:
                result.append(line)
        else:
            result.append(line)

    return '\n'.join(result)


def integrate_user_data(site_dir: Path) -> None:
    """
    Integrate user-data.md into main report for a single site.
    """
    site_name = site_dir.name
    main_file = None
    user_data_file = site_dir / 'user-data.md'

    # Find main report file
    for f in site_dir.glob('*.md'):
        if f.name != 'user-data.md':
            main_file = f
            break

    if not main_file or not main_file.exists():
        print(f"  ⚠️  No main report file found")
        return

    if not user_data_file.exists():
        print(f"  ⚠️  No user-data.md file")
        return

    # Read files
    main_content = main_file.read_text(encoding='utf-8')
    user_content = user_data_file.read_text(encoding='utf-8')

    # Track all anchors
    all_anchors = []

    # Extract and process each section
    sections_to_process = [
        ('Cancellation Stamp Locations', 'stamp'),
        ('Key Activities', 'activity'),
        ('Hidden Gems', 'gem'),
        ('Also Nearby', 'nearby')
    ]

    for section_title, prefix in sections_to_process:
        # Find section in main content and add anchors
        section_pattern = rf'(## {re.escape(section_title)}.*?)(?=\n## |\n---|\Z)'
        match = re.search(section_pattern, main_content, re.DOTALL)

        if match:
            section_content = match.group(1)
            modified_section, anchors = add_anchors_to_list_items(section_content, prefix)
            all_anchors.extend(anchors)
            main_content = main_content[:match.start()] + modified_section + main_content[match.end():]

    # Add links to user data checkboxes
    user_content = add_links_to_user_checkboxes(user_content, all_anchors)

    # Remove the "View Full Research Report" link from user data
    user_content = re.sub(r'\[View Full Research Report\]\([^)]+\)\n*', '', user_content)

    # Remove the site name header from user data (it will be # User Data)
    user_content = re.sub(r'^# [^\n]+\n*', '', user_content).strip()

    # Find where to insert User Data section (before the final "Total Recommended Time" line)
    total_time_pattern = r'(\n---\n\n\*\*Total Recommended.*?$)'
    match = re.search(total_time_pattern, main_content, re.MULTILINE | re.DOTALL)

    if match:
        insert_pos = match.start()
    else:
        # If no total time found, append at end
        insert_pos = len(main_content)

    # Create User Data section
    user_data_section = f"\n\n---\n\n# User Data\n\n{user_content}\n"

    # Insert User Data section
    new_main_content = main_content[:insert_pos] + user_data_section + main_content[insert_pos:]

    # Write updated main file
    main_file.write_text(new_main_content, encoding='utf-8')

    # Delete user-data.md
    user_data_file.unlink()

    print(f"  ✅ Integrated user data with {len(all_anchors)} anchor links")


def main():
    """Process all NPS sites"""
    nps_dir = Path('2-Enhanced Data/NPS')

    if not nps_dir.exists():
        print(f"Error: {nps_dir} not found")
        return

    sites = sorted([d for d in nps_dir.iterdir() if d.is_dir()])
    print(f"Processing {len(sites)} NPS sites...\n")

    for i, site_dir in enumerate(sites, 1):
        print(f"[{i}/{len(sites)}] {site_dir.name}")
        try:
            integrate_user_data(site_dir)
        except Exception as e:
            print(f"  ❌ Error: {e}")

    print(f"\n✅ Completed processing {len(sites)} sites")


if __name__ == '__main__':
    main()
