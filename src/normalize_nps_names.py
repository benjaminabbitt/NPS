#!/usr/bin/env python3
"""
Normalize NPS site names to filesystem-safe, consistent format
Renames directories to match standardized names from CSV
"""
import csv
import re
import shutil
from pathlib import Path
from typing import Dict, List, Tuple


def normalize_name(name: str) -> str:
    """
    Convert NPS site name to consistent filesystem-safe format

    Rules:
    1. Replace & with 'and'
    2. Remove periods from abbreviations (U.S. → US)
    3. Standardize spacing around punctuation
    4. Keep spaces (they're filesystem-safe)
    5. Remove trailing/leading whitespace
    6. Collapse multiple spaces to single space
    """
    # Basic cleanup
    name = name.strip()

    # Replace & with 'and'
    name = name.replace(' & ', ' and ')

    # Replace forward slash and underscore with space
    name = name.replace('/', ' ')
    name = name.replace('_', ' ')

    # Remove periods from abbreviations (but not from O'Neill, etc.)
    # Only remove period if followed by space or end of string
    name = re.sub(r'\.(?=\s|$)', '', name)

    # Normalize apostrophes - replace smart quote with regular apostrophe
    name = name.replace('\u2019', "'")  # Unicode right single quotation mark to apostrophe

    # Collapse multiple spaces
    name = re.sub(r'\s+', ' ', name)

    # Remove any characters that are problematic on filesystems
    # Allow: letters, numbers, spaces, hyphens, apostrophes, parentheses, commas
    name = re.sub(r'[^\w\s\-\'(),]', '', name)

    return name.strip()


def load_csv_names(csv_file: Path) -> List[str]:
    """Load all park names from CSV"""
    names = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header

        for row in reader:
            if len(row) >= 5:
                park_name = row[4].strip()
                if park_name:
                    names.append(park_name)

    return names


def find_existing_directory(normalized_name: str, base_dir: Path) -> Path:
    """Find existing directory that might match this normalized name"""
    # Try exact match first
    candidate = base_dir / normalized_name
    if candidate.exists():
        return candidate

    # Try case-insensitive match
    normalized_lower = normalized_name.lower()

    # Collect all potential matches with scores
    matches = []

    for dir_path in base_dir.iterdir():
        if not dir_path.is_dir():
            continue

        dir_lower = dir_path.name.lower()

        # Exact match (case-insensitive)
        if dir_lower == normalized_lower:
            return dir_path

        # Also check if existing directory name would normalize to the same thing
        # This handles cases where existing directory has underscores, etc.
        dir_normalized = normalize_name(dir_path.name).lower()
        if dir_normalized == normalized_lower:
            return dir_path

        # Extract key words (skip common abbreviations)
        def extract_key_words(s):
            words = s.lower().split()
            # Skip common abbreviations
            skip = {'nm', 'np', 'nhs', 'nhp', 'nmp', 'nb', 'nra', 'nl', 'ns', 'n', 'pres', 'mem', 'pkwy', 'nst', 'wr', 'nha', 'and', 'the'}
            return [w for w in words if w not in skip and len(w) > 2]

        norm_words = extract_key_words(normalized_name)
        dir_words = extract_key_words(dir_path.name)

        if not norm_words or not dir_words:
            continue

        # Calculate match score
        norm_set = set(norm_words)
        dir_set = set(dir_words)

        overlap = len(norm_set & dir_set)

        # Must have significant overlap AND similar lengths
        # This prevents "Theodore Roosevelt Island" from matching "Theodore Roosevelt NP"
        if overlap >= min(3, len(norm_words)):
            # Penalize if word counts are very different
            word_diff = abs(len(norm_words) - len(dir_words))
            score = overlap - (word_diff * 0.5)

            # Only consider if score is high enough and words match well
            if score >= min(3, len(norm_words) * 0.7):
                matches.append((score, dir_path))

    # Return best match if any
    if matches:
        matches.sort(reverse=True, key=lambda x: x[0])
        return matches[0][1]

    return None


def rename_directory_contents(old_dir: Path, new_name: str):
    """Rename files inside directory to match new directory name"""
    old_name = old_dir.name

    # Find files that use the old name
    for file_path in old_dir.glob('*'):
        if file_path.is_file() and file_path.stem == old_name:
            # Rename file to match new directory name
            new_file = file_path.parent / f"{new_name}{file_path.suffix}"
            if not new_file.exists():
                file_path.rename(new_file)
                print(f"      Renamed file: {file_path.name} → {new_file.name}")


def create_name_mapping(csv_file: Path, base_dir: Path) -> Dict[str, Tuple[str, Path]]:
    """
    Create mapping of CSV names to (normalized_name, existing_directory)
    """
    csv_names = load_csv_names(csv_file)

    mapping = {}

    for csv_name in csv_names:
        normalized = normalize_name(csv_name)
        existing = find_existing_directory(normalized, base_dir)
        mapping[csv_name] = (normalized, existing)

    return mapping


def rename_directories(mapping: Dict[str, Tuple[str, Path]], base_dir: Path, dry_run: bool = True):
    """
    Rename directories to match normalized names
    """
    renamed_count = 0
    created_count = 0
    skipped_count = 0

    # Track which source directories have been renamed
    renamed_dirs = set()

    for csv_name, (normalized_name, existing_dir) in sorted(mapping.items()):
        target_dir = base_dir / normalized_name

        if existing_dir is None:
            print(f"  ✗ No existing directory found for: {csv_name}")
            print(f"    Would create: {normalized_name}")
            skipped_count += 1
            continue

        # Skip if this directory was already renamed
        if existing_dir in renamed_dirs:
            print(f"  ⚠ Already renamed: {existing_dir.name}")
            print(f"    CSV entry: {csv_name} → {normalized_name}")
            skipped_count += 1
            continue

        if existing_dir.name == normalized_name:
            # Already correctly named
            continue

        if target_dir.exists() and target_dir != existing_dir:
            print(f"  ⚠ Target already exists: {normalized_name}")
            print(f"    Existing: {existing_dir.name}")
            skipped_count += 1
            continue

        print(f"  Renaming: {existing_dir.name}")
        print(f"        → {normalized_name}")

        if not dry_run:
            # Rename directory
            existing_dir.rename(target_dir)

            # Rename files inside to match new directory name
            rename_directory_contents(target_dir, normalized_name)

            # Mark this directory as renamed
            renamed_dirs.add(existing_dir)

            renamed_count += 1
        else:
            renamed_count += 1

    return renamed_count, created_count, skipped_count


def show_translation_examples(mapping: Dict[str, Tuple[str, Path]]):
    """Show examples of name translations"""
    print("\nName Translation Examples:")
    print("=" * 70)

    shown = 0
    for csv_name, (normalized_name, existing_dir) in sorted(mapping.items()):
        if csv_name != normalized_name:
            existing_name = existing_dir.name if existing_dir else "(not found)"
            print(f"CSV:    {csv_name}")
            print(f"Normal: {normalized_name}")
            print(f"Exists: {existing_name}")
            print()

            shown += 1
            if shown >= 10:
                break

    # Count total changes
    changes = sum(1 for csv, (norm, _) in mapping.items() if csv != norm)
    print(f"Total names requiring normalization: {changes}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Normalize NPS site names')
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Show what would be renamed without actually renaming (default)')
    parser.add_argument('--execute', action='store_true',
                        help='Actually perform the renames')
    parser.add_argument('--show-examples', action='store_true',
                        help='Show translation examples only')

    args = parser.parse_args()

    csv_file = Path("1-Raw Input Data/NPS/Untitled spreadsheet - US Parks.csv")
    base_dir = Path("2-Enhanced Data/NPS")

    if not csv_file.exists():
        print(f"Error: CSV file not found at {csv_file}")
        return

    if not base_dir.exists():
        print(f"Error: Base directory not found at {base_dir}")
        return

    print("=" * 70)
    print("NPS SITE NAME NORMALIZATION")
    print("=" * 70)
    print()

    # Create mapping
    print("Building name mapping...")
    mapping = create_name_mapping(csv_file, base_dir)
    print(f"Processed {len(mapping)} sites from CSV")

    if args.show_examples:
        show_translation_examples(mapping)
        return

    # Show what will be done
    dry_run = not args.execute

    if dry_run:
        print("\n*** DRY RUN MODE - No changes will be made ***")
        print("Use --execute to actually rename directories\n")
    else:
        print("\n*** EXECUTING RENAMES ***\n")

    # Perform renames
    renamed, created, skipped = rename_directories(mapping, base_dir, dry_run=dry_run)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Directories to rename: {renamed}")
    print(f"New directories to create: {created}")
    print(f"Skipped: {skipped}")

    if dry_run:
        print("\nTo execute these changes, run with --execute flag:")
        print("  python3 src/normalize_nps_names.py --execute")


if __name__ == '__main__':
    main()
