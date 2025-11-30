#!/usr/bin/env python3
"""
Merge duplicate NPS site directories.
Copies content from old (underscore) directories to new (apostrophe/comma) directories,
renames files to match new directory names, then removes old directories.
"""
import shutil
from pathlib import Path
from typing import List, Tuple

# Define duplicate pairs: (new_name, old_name)
DUPLICATE_PAIRS: List[Tuple[str, str]] = [
    # Apostrophe vs underscore duplicates
    ("Belmont-Paul Women's Equality NM", "Belmont-Paul Women_s Equality NM"),
    ("Bent's Old Fort NHS", "Bent_s Old Fort NHS"),
    ("Ebey's Landing NH RES", "Ebey_s Landing NH RES"),
    ("Eugene O'Neill NHS", "Eugene O_Neill NHS"),
    ("Ford's Theatre NHS", "Ford_s Theatre NHS"),
    ("Pu'uhonua o Honaunau NHP", "Pu_uhonua o Honaunau NHP"),
    ("Pu'ukohola Heiau NHS", "Pu_ukohola Heiau NHS"),
    ("Saint Paul's Church NHS", "Saint Paul_s Church NHS"),
    ("The Lockkeeper's House", "The Lockkeeper_s House"),
    ("Vietnam Women's MEM", "Vietnam Women_s MEM"),
    ("Women's Rights NHP", "Women_s Rights NHP"),
    # Comma vs underscore duplicates
    ("John D Rockefeller, Jr Memorial Parkway", "John D_ Rockefeller_ Jr_ Memorial Parkway"),
    ("Martin Luther King, Jr NHP", "Martin Luther King_ Jr_ NHP"),
    # Period/dot duplicates
    ("US Navy MEM", "U_S_ Navy MEM"),
    # Ampersand vs underscore
    ("Wrangell-St Elias NP and PRES", "Wrangell-St_ Elias NP _ PRES"),
    # Cedar Creek has & in filename
    ("Cedar Creek and Belle Grove NHP", "Cedar Creek _ Belle Grove NHP"),
]


def merge_directories(base_dir: Path, dry_run: bool = True) -> None:
    """Merge old directories into new ones."""
    for new_name, old_name in DUPLICATE_PAIRS:
        new_dir = base_dir / new_name
        old_dir = base_dir / old_name

        if not old_dir.exists():
            print(f"SKIP: Old directory not found: {old_name}")
            continue

        if not new_dir.exists():
            # Just rename the old directory to new name
            print(f"RENAME: {old_name} → {new_name}")
            if not dry_run:
                old_dir.rename(new_dir)
                # Rename files inside to match new directory name
                rename_files_in_dir(new_dir, old_name, new_name)
            continue

        print(f"\nMERGE: {old_name} → {new_name}")

        # Copy files from old to new (don't overwrite existing)
        for old_file in old_dir.iterdir():
            if not old_file.is_file():
                continue

            # Determine new filename
            new_filename = old_file.name.replace(old_name, new_name)
            # Also handle underscores that should be apostrophes in filenames
            new_filename = normalize_filename(new_filename, new_name)

            new_file = new_dir / new_filename

            if new_file.exists():
                # Check if old file has more content
                old_size = old_file.stat().st_size
                new_size = new_file.stat().st_size

                if old_size > new_size:
                    print(f"  REPLACE: {old_file.name} ({old_size}b) → {new_filename} ({new_size}b)")
                    if not dry_run:
                        shutil.copy2(old_file, new_file)
                else:
                    print(f"  KEEP: {new_filename} (new: {new_size}b >= old: {old_size}b)")
            else:
                print(f"  COPY: {old_file.name} → {new_filename}")
                if not dry_run:
                    shutil.copy2(old_file, new_file)

        # Remove old directory
        print(f"  DELETE: {old_name}/")
        if not dry_run:
            shutil.rmtree(old_dir)


def normalize_filename(filename: str, dir_name: str) -> str:
    """Normalize a filename to match directory naming convention."""
    # If file is named after directory, use directory name
    base, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')

    # Check if this appears to be the main site file
    # by checking if it contains key words from the directory name
    dir_words = set(dir_name.lower().split())
    file_words = set(base.lower().replace('_', ' ').split())

    overlap = len(dir_words & file_words)
    if overlap >= 2:
        # This is likely the main site file, rename to match directory
        return f"{dir_name}.{ext}" if ext else dir_name

    return filename


def rename_files_in_dir(dir_path: Path, old_name: str, new_name: str) -> None:
    """Rename files inside directory to match new directory name."""
    for file_path in dir_path.iterdir():
        if not file_path.is_file():
            continue

        # Check if filename contains old name pattern
        if old_name in file_path.name or old_name.replace(' ', '_') in file_path.name:
            new_filename = file_path.name.replace(old_name, new_name)
            # Also replace underscore patterns
            new_filename = new_filename.replace(old_name.replace("'", "_"), new_name)

            new_file = file_path.parent / new_filename
            if new_file != file_path:
                print(f"  RENAME FILE: {file_path.name} → {new_filename}")
                file_path.rename(new_file)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Merge duplicate NPS directories')
    parser.add_argument('--execute', action='store_true',
                        help='Actually perform merges (default is dry-run)')
    args = parser.parse_args()

    base_dir = Path("2-Enhanced Data/NPS")

    if not base_dir.exists():
        print(f"Error: Base directory not found: {base_dir}")
        return

    print("=" * 70)
    print("NPS DUPLICATE DIRECTORY MERGER")
    print("=" * 70)

    if not args.execute:
        print("\n*** DRY RUN MODE - No changes will be made ***")
        print("Use --execute to actually merge directories\n")
    else:
        print("\n*** EXECUTING MERGES ***\n")

    merge_directories(base_dir, dry_run=not args.execute)

    print("\n" + "=" * 70)
    print("COMPLETE")
    print("=" * 70)

    if not args.execute:
        print("\nTo execute these changes, run:")
        print("  python3 src/nps_site/merge_duplicate_dirs.py --execute")


if __name__ == '__main__':
    main()
