#!/usr/bin/env python3
"""
Merge duplicate NPS directories - move data from old (underscore) to new (clean) versions
"""
from pathlib import Path
import shutil


def merge_directories(old_dir: Path, new_dir: Path, dry_run: bool = True):
    """Move all files from old_dir to new_dir, then delete old_dir"""
    if not old_dir.exists():
        print(f"  ⚠ Old directory doesn't exist: {old_dir.name}")
        return False

    if not new_dir.exists():
        print(f"  ⚠ New directory doesn't exist: {new_dir.name}")
        return False

    print(f"Merging: {old_dir.name}")
    print(f"    → {new_dir.name}")

    # List all files in old directory
    files_moved = 0
    files_skipped = 0

    for file_path in old_dir.glob('*'):
        if file_path.is_file():
            target_file = new_dir / file_path.name

            if target_file.exists():
                print(f"    ⚠ Skip (exists): {file_path.name}")
                files_skipped += 1
            else:
                print(f"    → Move: {file_path.name}")
                if not dry_run:
                    shutil.move(str(file_path), str(target_file))
                files_moved += 1

    # Remove old directory if empty
    if not dry_run:
        try:
            old_dir.rmdir()
            print(f"    ✓ Removed empty directory: {old_dir.name}")
        except OSError as e:
            print(f"    ⚠ Could not remove directory: {e}")

    print(f"    Files moved: {files_moved}, skipped: {files_skipped}")
    print()

    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Merge duplicate NPS directories')
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Show what would be done (default)')
    parser.add_argument('--execute', action='store_true',
                        help='Actually perform the merge')

    args = parser.parse_args()

    base_dir = Path("2-Enhanced Data/NPS")

    # List of known duplicates (old_name, new_name)
    duplicates = [
        ("Belmont-Paul Women_s Equality NM", "Belmont-Paul Women's Equality NM"),
        ("Bent_s Old Fort NHS", "Bent's Old Fort NHS"),
        ("Cedar Creek _ Belle Grove NHP", "Cedar Creek and Belle Grove NHP"),
        ("Ebey_s Landing NH RES", "Ebey's Landing NH RES"),
        ("Ford_s Theatre NHS", "Ford's Theatre NHS"),
        ("Saint Paul_s Church NHS", "Saint Paul's Church NHS"),
        ("The Lockkeeper_s House", "The Lockkeeper's House"),
        ("U_S_ Navy MEM", "US Navy MEM"),
        ("Vietnam Women_s MEM", "Vietnam Women's MEM"),
        ("Women_s Rights NHP", "Women's Rights NHP"),
        ("Wrangell-St_ Elias NP _ PRES", "Wrangell-St Elias NP and PRES"),
    ]

    print("=" * 70)
    print("NPS DIRECTORY MERGE")
    print("=" * 70)

    dry_run = not args.execute
    if dry_run:
        print("\n*** DRY RUN MODE - No changes will be made ***\n")
    else:
        print("\n*** EXECUTING MERGE ***\n")

    merged_count = 0

    for old_name, new_name in duplicates:
        old_dir = base_dir / old_name
        new_dir = base_dir / new_name

        if old_dir.exists() and new_dir.exists():
            if merge_directories(old_dir, new_dir, dry_run):
                merged_count += 1

    print("=" * 70)
    print(f"Directories merged: {merged_count}")

    if dry_run and merged_count > 0:
        print("\nTo execute, run with --execute flag:")
        print("  python3 src/merge_duplicate_nps_dirs.py --execute")


if __name__ == '__main__':
    main()
