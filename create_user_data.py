#!/usr/bin/env python3
"""
Create user-data.md files with checkboxes for visited and activities
"""

from pathlib import Path
import re


def extract_activities(content: str, site_file_name: str) -> list:
    """Extract activities from site markdown content"""

    activities = []
    lines = content.split('\n')

    current_section = None
    i = 0

    while i < len(lines):
        line = lines[i]

        # Detect sections
        if line.strip() == '## Key Activities':
            current_section = 'key'
        elif line.strip() == '## Hidden Gems':
            current_section = 'hidden'
        elif line.strip() == '## Also Nearby':
            current_section = 'nearby'
        elif line.startswith('## ') and line.strip() not in ['## Key Activities', '## Hidden Gems', '## Also Nearby']:
            current_section = None

        # Extract checkbox items
        if current_section and line.strip().startswith('- [ ]'):
            # Parse activity line format:
            # - [ ] Activity name (time) - Description; address; hours [Sources]

            # Remove the checkbox
            activity_text = line.strip()[6:]  # Remove "- [ ] "

            # Try to extract name and timing
            # Pattern: Name (time) - rest...
            match = re.match(r'^(.+?)\s*\(([^)]+)\)\s*[-–]\s*(.+)', activity_text)

            if match:
                name = match.group(1).strip()
                time = match.group(2).strip()

                # Create anchor link (lowercase, replace spaces with hyphens)
                section_anchor = current_section.replace(' ', '-').lower()
                if current_section == 'key':
                    section_name = 'Key Activities'
                elif current_section == 'hidden':
                    section_name = 'Hidden Gems'
                else:
                    section_name = 'Also Nearby'

                activity = {
                    'name': name,
                    'time': time,
                    'section': section_name,
                    'link': f"{site_file_name}#{section_name.lower().replace(' ', '-')}"
                }

                activities.append(activity)
            else:
                # Fallback: just use the whole text as name
                # Try to find timing in parentheses
                time_match = re.search(r'\(([^)]+)\)', activity_text)
                if time_match:
                    time = time_match.group(1)
                    name = activity_text[:time_match.start()].strip()
                else:
                    name = activity_text.split('-')[0].strip() if '-' in activity_text else activity_text
                    time = "Time not specified"

                section_name = 'Key Activities' if current_section == 'key' else 'Hidden Gems' if current_section == 'hidden' else 'Also Nearby'

                activity = {
                    'name': name,
                    'time': time,
                    'section': section_name,
                    'link': f"{site_file_name}#{section_name.lower().replace(' ', '-')}"
                }

                activities.append(activity)

        i += 1

    return activities


def create_user_data_file(site_dir: Path, site_name: str):
    """Create user-data.md for a site"""

    # Read site markdown file
    site_file = site_dir / f"{site_name}.md"

    if not site_file.exists():
        print(f"  Warning: {site_file} not found, creating minimal user-data.md")
        user_data = f"# {site_name}\n\n- [ ] Visited\n\n## Activities\n\nNo activities parsed from site file.\n"
        user_data_file = site_dir / "user-data.md"
        user_data_file.write_text(user_data, encoding='utf-8')
        return

    with open(site_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract activities
    activities = extract_activities(content, site_file.name)

    # Create user-data.md content
    user_data = f"# {site_name}\n\n"
    user_data += "- [ ] Visited\n\n"

    if activities:
        user_data += "## Activities\n\n"

        # Group by section
        sections = {}
        for activity in activities:
            section = activity['section']
            if section not in sections:
                sections[section] = []
            sections[section].append(activity)

        # Write activities by section
        for section_name in ['Key Activities', 'Hidden Gems', 'Also Nearby']:
            if section_name in sections:
                user_data += f"### {section_name}\n\n"
                for activity in sections[section_name]:
                    user_data += f"- [ ] {activity['name']} ({activity['time']}) - [Details]({activity['link']})\n"
                user_data += "\n"
    else:
        user_data += "## Activities\n\n"
        user_data += f"No activities found. See [{site_file.name}]({site_file.name}) for details.\n"

    # Write user-data.md
    user_data_file = site_dir / "user-data.md"
    user_data_file.write_text(user_data, encoding='utf-8')

    # Remove old override.md if it exists
    override_file = site_dir / "override.md"
    if override_file.exists():
        override_file.unlink()


def main():
    enhanced_dir = Path("2-Enhanced Data")

    if not enhanced_dir.exists():
        print("Error: 2-Enhanced Data directory not found")
        return

    site_dirs = [d for d in enhanced_dir.iterdir() if d.is_dir()]

    print(f"Creating user-data.md files for {len(site_dirs)} sites...")
    print("="*70)

    for i, site_dir in enumerate(site_dirs, 1):
        site_name = site_dir.name
        create_user_data_file(site_dir, site_name)

        if i % 50 == 0:
            print(f"  Processed {i}/{len(site_dirs)} sites")

    print("="*70)
    print(f"Complete! Created {len(site_dirs)} user-data.md files")
    print()
    print("Each user-data.md includes:")
    print("  - [ ] Visited checkbox")
    print("  - [ ] Activity checkboxes with:")
    print("      - Activity name")
    print("      - Estimated time")
    print("      - Link to details in site .md file")


if __name__ == '__main__':
    main()
