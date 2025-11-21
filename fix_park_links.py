#!/usr/bin/env python3
"""
Fix park markdown files to properly link coaster files
"""

from pathlib import Path

base_dir = Path("Amusement Parks")

# Find all park directories
park_dirs = [d for d in base_dir.iterdir() if d.is_dir() and d.name != "Inputs"]

print(f"Processing {len(park_dirs)} parks...")

for park_dir in park_dirs:
    park_file = park_dir / f"{park_dir.name}.md"

    if not park_file.exists():
        continue

    # Get all coaster markdown files in this directory
    coaster_files = {f.stem: f.name for f in park_dir.glob("*.md") if f.name != park_file.name}

    if not coaster_files:
        print(f"No coaster files in {park_dir.name}")
        continue

    # Read the park file
    with open(park_file, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    new_lines = []
    in_coaster_section = False
    updated = False

    for i, line in enumerate(lines):
        if '## Coasters at This Park' in line:
            in_coaster_section = True
            new_lines.append(line)
            new_lines.append('')  # Add blank line after header
        elif in_coaster_section:
            if line.strip().startswith('- ') and not line.strip().startswith('- ['):
                # This is an unlinked coaster name
                coaster_name = line.strip()[2:].strip()

                # Try to find matching file
                matched_file = None
                for stem, filename in coaster_files.items():
                    if stem == coaster_name or stem.replace('_', ' ') == coaster_name:
                        matched_file = filename
                        break

                if matched_file:
                    new_line = f"- [{coaster_name}]({matched_file})"
                    new_lines.append(new_line)
                    updated = True
                else:
                    new_lines.append(line)
            elif line.strip() == '' and i + 1 < len(lines) and not lines[i + 1].strip().startswith('- '):
                # End of list
                in_coaster_section = False
                new_lines.append(line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    if updated:
        # Write back
        with open(park_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        print(f"Updated {park_dir.name}")
    else:
        print(f"  Skipped {park_dir.name} (no changes)")

print("\nDone!")
