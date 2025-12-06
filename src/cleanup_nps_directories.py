#!/usr/bin/env python3
"""
Clean up NPS directory names: replace underscores with apostrophes or remove them
"""
from pathlib import Path
import shutil


def clean_name(name: str) -> str:
    """
    Clean up directory/file names:
    - Replace _s with 's (possessives)
    - Replace _ _ with ' and ' (e.g., Cedar Creek _ Belle Grove)
    - Replace U_S_ with US
    - Replace other underscores followed by space with apostrophe
    """
    # Specific replacements first
    name = name.replace(' _ ', ' and ')  # Cedar Creek _ Belle Grove
    name = name.replace('U_S_', 'US')     # U.S. → US
    name = name.replace('_s ', "'s ")     # possessives
    name = name.replace('_', '')          # Remove remaining underscores

    return name


def rename_directory_and_files(dir_path: Path, new_name: str):
    """Rename directory and its main report file"""
    old_name = dir_path.name
    new_dir = dir_path.parent / new_name

    if new_dir.exists() and new_dir != dir_path:
        print(f"  ⚠ Target exists: {new_name}")
        return False

    # Rename the directory
    dir_path.rename(new_dir)
    print(f"  ✓ Renamed: {old_name} → {new_name}")

    # Rename main report file if it exists
    old_report = new_dir / f"{old_name}.md"
    new_report = new_dir / f"{new_name}.md"

    if old_report.exists() and not new_report.exists():
        old_report.rename(new_report)
        print(f"    ✓ Renamed file: {old_name}.md → {new_name}.md")

    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Clean up NPS directory names')
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Show what would be renamed (default)')
    parser.add_argument('--execute', action='store_true',
                        help='Actually perform the renames')

    args = parser.parse_args()

    base_dir = Path("2-Enhanced Data/NPS")

    if not base_dir.exists():
        print(f"Error: {base_dir} not found")
        return

    print("=" * 70)
    print("NPS DIRECTORY CLEANUP")
    print("=" * 70)

    dry_run = not args.execute
    if dry_run:
        print("\n*** DRY RUN MODE - No changes will be made ***\n")
    else:
        print("\n*** EXECUTING RENAMES ***\n")

    renamed_count = 0

    # Find all directories with underscores
    for dir_path in sorted(base_dir.iterdir()):
        if not dir_path.is_dir() or dir_path.name == ".git":
            continue

        if '_' in dir_path.name:
            cleaned = clean_name(dir_path.name)

            if cleaned != dir_path.name:
                print(f"{dir_path.name}")
                print(f"  → {cleaned}")

                if not dry_run:
                    if rename_directory_and_files(dir_path, cleaned):
                        renamed_count += 1
                else:
                    renamed_count += 1

                print()

    print("=" * 70)
    print(f"Directories to rename: {renamed_count}")

    if dry_run and renamed_count > 0:
        print("\nTo execute, run with --execute flag:")
        print("  python3 src/cleanup_nps_directories.py --execute")


if __name__ == '__main__':
    main()
