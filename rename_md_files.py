#!/usr/bin/env python3
"""Rename all _md files to .md"""

from pathlib import Path

base_dir = Path("Amusement Parks")

# Find all files ending with _md
files_to_rename = list(base_dir.rglob("*_md"))

print(f"Found {len(files_to_rename)} files to rename")

for old_path in files_to_rename:
    new_path = old_path.with_name(old_path.name[:-3] + ".md")

    try:
        old_path.rename(new_path)
        print(f"Renamed: {old_path.name} -> {new_path.name}")
    except Exception as e:
        print(f"Error renaming {old_path}: {e}")

print(f"\nDone! Renamed {len(files_to_rename)} files")
