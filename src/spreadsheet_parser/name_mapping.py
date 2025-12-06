#!/usr/bin/env python3
"""
NPS Site Name to Directory Path Mapping

This module provides consistent normalization and mapping between
CSV park names and filesystem directory names.
"""

from pathlib import Path

# Base path for enhanced NPS data
ENHANCED_DATA_PATH = Path("/workspace/2-Enhanced Data/NPS")

# Explicit name mappings for known mismatches
# Key: normalized CSV name (lowercase), Value: actual directory name
EXPLICIT_MAPPINGS = {
    # Naming variations with periods, apostrophes, special chars
    "wrangell-st. elias np & pres": "Wrangell-St Elias NP and PRES",
    "sequoia  np": "Sequoia NP",  # Double space issue
    "ste. genevieve nhp": "Ste Genevieve NHP",
    "ste. geneviève nhp": "Ste Genevieve NHP",  # With accent
    "wilson's creek nb": "Wilson’s Creek NB",  # U+2019 curly quote in directory name
    "mt. rushmore n mem": "Mount Rushmore N MEM",

    # Mississippi sites
    "brices cross roads nbs": "Brices Cross Roads NBS",
    "natchez trace nst": "Natchez Trace NST",
    "natchez trace pkwy": "Natchez Trace PKWY",
    "tupelo nb": "Tupelo NB",
    "vicksburg nmp": "Vicksburg NMP",

    # Missouri sites
    "gateway arch np": "Gateway Arch NP",
    "ozark nsr": "Ozark NSR",

    # Nebraska
    "niobrara nsr": "Niobrara NSR",

    # North Dakota
    "fort union trading post nhs": "Fort Union Trading Post NHS",
    "knife river indian villages nhs": "Knife River Indian Villages NHS",

    # Ohio (existing directory - use "and" version)
    "perry's victory & international peace mem": "Perry's Victory and International Peace MEM",

    # Oregon/Washington (existing directory - use "and" version)
    "lewis & clark nat'l & state historical parks": "Lewis and Clark Nat'l and State Historical Parks",

    # Hawaii (use apostrophe versions)
    "pu'uhonua o honaunau nhp": "Pu'uhonua o Honaunau NHP",
    "pu'ukohola heiau nhs": "Pu'ukohola Heiau NHS",

    # California (use apostrophe version)
    "eugene o'neill nhs": "Eugene O'Neill NHS",

    # Wyoming (use no-comma version which is larger)
    "john d. rockefeller, jr. memorial parkway": "John D Rockefeller Jr Memorial Parkway",

    # Georgia (use comma version which is larger)
    "martin luther king, jr. nhp": "Martin Luther King, Jr NHP",

    # South Dakota
    "jewel cave nm": "Jewel Cave NM",
    "minuteman missile nhs": "Minuteman Missile NHS",
    "missouri nrr": "Missouri NRR",
    "wind cave np": "Wind Cave NP",

    # DC sites with data issues
    "mary mcleod bethune council house nhs;": "Mary McLeod Bethune Council House NHS",
    "mary mcleod bethune council house nhs": "Mary McLeod Bethune Council House NHS",
    "theodore roosevelt island": "Theodore Roosevelt Island",

    # Common & vs "and" variations
    "denali np & pres": "Denali NP & PRES",
    "glacier bay np & pres": "Glacier Bay NP & PRES",
    "gates of the arctic np & pres": "Gates of the Arctic NP and PRES",
    "katmai np & pres": "Katmai NP and PRES",
    "lake clark np & pres": "Lake Clark NP and PRES",
    "aniakchak nm & pres": "Aniakchak NM and PRES",
    "great sand dunes np & pres": "Great Sand Dunes NP and PRES",
    "chickamauga & chattanooga nmp": "Chickamauga and Chattanooga NMP",
    "cedar creek & belle grove nhp": "Cedar Creek and Belle Grove NHP",
}


def normalize_name(name: str) -> str:
    """
    Normalize a park name for comparison.

    - Lowercase
    - Strip whitespace
    - Collapse multiple spaces
    - Remove trailing punctuation
    - Normalize curly quotes to straight quotes
    """
    if not name:
        return ""

    # Strip and lowercase
    normalized = name.strip().lower()

    # Normalize curly/smart quotes to straight quotes
    # U+2019 RIGHT SINGLE QUOTATION MARK -> U+0027 APOSTROPHE
    # U+2018 LEFT SINGLE QUOTATION MARK -> U+0027 APOSTROPHE
    normalized = normalized.replace('\u2019', "'").replace('\u2018', "'")

    # Collapse multiple spaces
    while "  " in normalized:
        normalized = normalized.replace("  ", " ")

    # Remove trailing semicolons or other punctuation
    normalized = normalized.rstrip(";,.")

    return normalized


def get_directory_name(csv_name: str) -> str:
    """
    Get the directory name for a CSV park name.

    Args:
        csv_name: The park name as it appears in the CSV

    Returns:
        The directory name to use (may need to be created)
    """
    if not csv_name:
        return ""

    normalized = normalize_name(csv_name)

    # Check explicit mappings first
    if normalized in EXPLICIT_MAPPINGS:
        return EXPLICIT_MAPPINGS[normalized]

    # Try to find existing directory with various normalizations
    dir_name = find_existing_directory(csv_name)
    if dir_name:
        return dir_name

    # Default: clean up the CSV name for use as directory name
    return clean_for_directory(csv_name)


def clean_for_directory(name: str) -> str:
    """
    Clean a name for use as a directory name.

    - Remove trailing punctuation
    - Collapse multiple spaces
    - Keep & and other chars that appear in existing directories
    """
    if not name:
        return ""

    cleaned = name.strip()

    # Remove trailing punctuation
    cleaned = cleaned.rstrip(";,.")

    # Collapse multiple spaces
    while "  " in cleaned:
        cleaned = cleaned.replace("  ", " ")

    return cleaned


def find_existing_directory(csv_name: str) -> str | None:
    """
    Try to find an existing directory matching the CSV name.

    Returns the directory name if found, None otherwise.
    """
    if not csv_name or not ENHANCED_DATA_PATH.exists():
        return None

    normalized = normalize_name(csv_name)

    # Build variations to try
    variations = [
        csv_name.strip(),
        csv_name.strip().replace("&", "and"),
        csv_name.strip().replace(" & ", " and "),
        csv_name.strip().replace(".", ""),
        csv_name.strip().replace("'", ""),
        csv_name.strip().replace("'", "'"),
        csv_name.strip().rstrip(";,."),
    ]

    # Also try with collapsed spaces
    for var in list(variations):
        collapsed = var
        while "  " in collapsed:
            collapsed = collapsed.replace("  ", " ")
        if collapsed != var:
            variations.append(collapsed)

    # Try exact matches first
    for var in variations:
        for dir_path in ENHANCED_DATA_PATH.iterdir():
            if dir_path.is_dir() and dir_path.name == var:
                return dir_path.name

    # Try case-insensitive matches
    for var in variations:
        var_lower = var.lower()
        for dir_path in ENHANCED_DATA_PATH.iterdir():
            if dir_path.is_dir() and dir_path.name.lower() == var_lower:
                return dir_path.name

    # Try normalized comparison (ignoring punctuation)
    import re
    for dir_path in ENHANCED_DATA_PATH.iterdir():
        if dir_path.is_dir():
            dir_normalized = re.sub(r'[^\w\s]', ' ', dir_path.name).lower()
            csv_normalized = re.sub(r'[^\w\s]', ' ', normalized)
            # Collapse spaces in both
            dir_normalized = ' '.join(dir_normalized.split())
            csv_normalized = ' '.join(csv_normalized.split())
            if dir_normalized == csv_normalized:
                return dir_path.name

    return None


def get_directory_path(csv_name: str) -> Path:
    """
    Get the full path to the directory for a CSV park name.

    Args:
        csv_name: The park name as it appears in the CSV

    Returns:
        Path object for the directory
    """
    dir_name = get_directory_name(csv_name)
    return ENHANCED_DATA_PATH / dir_name


def directory_exists(csv_name: str) -> bool:
    """Check if a directory exists for the given CSV name."""
    path = get_directory_path(csv_name)
    return path.exists() and path.is_dir()


def user_data_exists(csv_name: str) -> bool:
    """Check if user-data.md exists for the given CSV name."""
    path = get_directory_path(csv_name) / "user-data.md"
    return path.exists()


# Abbreviation expansions for full names
ABBREVIATION_EXPANSIONS = {
    "NP": "National Park",
    "NHP": "National Historical Park",
    "NHS": "National Historic Site",
    "NM": "National Monument",
    "NMP": "National Military Park",
    "NB": "National Battlefield",
    "NBS": "National Battlefield Site",
    "NBP": "National Battlefield Park",
    "NRA": "National Recreation Area",
    "NL": "National Lakeshore",
    "NS": "National Seashore",
    "N PRES": "National Preserve",
    "PRES": "Preserve",
    "N MEM": "National Memorial",
    "MEM": "Memorial",
    "PKWY": "Parkway",
    "NST": "National Scenic Trail",
    "NHT": "National Historic Trail",
    "NSR": "National Scenic River",
    "NRR": "National Recreational River",
    "WSR": "Wild and Scenic River",
    "WR": "Wild River",
    "NHA": "National Heritage Area",
    "N RES": "National Reserve",
    "IHS": "International Historic Site",
    "SRR": "Scenic and Recreational River",
}


def expand_abbreviation(name: str) -> str:
    """
    Expand abbreviations in a park name.

    Example: "Yellowstone NP" -> "Yellowstone NP (National Park)"
    """
    if not name:
        return ""

    # Try to match abbreviations at the end of the name
    for abbrev, expansion in sorted(ABBREVIATION_EXPANSIONS.items(), key=lambda x: -len(x[0])):
        if name.endswith(f" {abbrev}"):
            return f"{name} ({expansion})"
        if name.endswith(f" {abbrev} &") or f" {abbrev} &" in name:
            # Handle cases like "NP & PRES"
            continue

    # Handle compound endings like "NP & PRES" or "NP and PRES"
    for connector in [" & ", " and "]:
        if connector in name:
            parts = name.split(connector)
            if len(parts) == 2:
                first_expanded = expand_abbreviation(parts[0])
                second_abbrev = parts[1].strip()
                if second_abbrev in ABBREVIATION_EXPANSIONS:
                    if first_expanded != parts[0]:
                        # First part was expanded, just add the second expansion
                        return f"{name} ({ABBREVIATION_EXPANSIONS[second_abbrev]})"

    return name


if __name__ == "__main__":
    # Test the mappings
    test_names = [
        "Wrangell-St. Elias NP & PRES",
        "Sequoia  NP",
        "Gateway Arch NP",
        "Denali NP & PRES",
        "Mary McLeod Bethune Council House NHS;",
    ]

    print("Testing name mappings:\n")
    for name in test_names:
        dir_name = get_directory_name(name)
        exists = directory_exists(name)
        user_data = user_data_exists(name)
        print(f"CSV: {name!r}")
        print(f"  -> Dir: {dir_name}")
        print(f"  -> Exists: {exists}, user-data.md: {user_data}")
        print()
