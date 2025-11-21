#!/usr/bin/env python3
"""
Update park markdown files to link to coaster files
"""

from pathlib import Path
import re

base_dir = Path("Amusement Parks")

# Find all park directories
park_dirs = [d for d in base_dir.iterdir() if d.is_dir() and d.name != "Inputs"]

print(f"Processing {len(park_dirs)} parks...")

for park_dir in park_dirs:
    park_file = park_dir / f"{park_dir.name}.md"

    if not park_file.exists():
        print(f"Warning: No park file found at {park_file}")
        continue

    # Read the park file
    with open(park_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the "Coasters at This Park" section
    lines = content.split('\n')
    new_lines = []
    in_coaster_section = False

    for line in lines:
        if '## Coasters at This Park' in line:
            in_coaster_section = True
            new_lines.append(line)
        elif in_coaster_section and line.strip().startswith('- '):
            # This is a coaster name
            coaster_name = line.strip()[2:].strip()  # Remove "- "

            # Create filename (sanitize)
            filename = coaster_name + ".md"

            # Check if file exists
            coaster_file = park_dir / filename
            if coaster_file.exists():
                # Create link
                new_line = f"- [{coaster_name}]({filename})"
                new_lines.append(new_line)
                print(f"  Linked: {coaster_name}")
            else:
                # Keep original if file doesn't exist
                new_lines.append(line)
                print(f"  Warning: File not found for {coaster_name}")
        elif in_coaster_section and line.strip() == '':
            # End of coaster section
            in_coaster_section = False
            new_lines.append(line)
        else:
            new_lines.append(line)

    # Write updated content
    with open(park_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))

    print(f"Updated: {park_file.name}\n")

print("Done! All park files updated with coaster links.")
