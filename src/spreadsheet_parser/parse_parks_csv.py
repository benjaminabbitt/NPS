#!/usr/bin/env python3
"""
Parse the US Parks CSV spreadsheet and update user-data.md files with
visitor center and park information including geocodes.

CSV Column Structure:
  [0]: State label (e.g., "ALABAMA:")
  [1]: In the Book
  [2]: Completed
  [3]: Est. Hours
  [4]: National Park name
  [5-8]: Park Address, City, State, Zip
  [9-15]: Park hours (Sun-Sat)
  [16]: (empty separator)
  [17]: Visitor Center Location name
  [18-21]: VC Address, City, State, Zip
  [22-28]: VC hours (Sun-Sat)
"""

import csv
import os
import re
import time
import urllib.parse
import urllib.request
import json
from pathlib import Path

from name_mapping import (
    get_directory_path,
    directory_exists,
    normalize_name,
)

# Paths
CSV_PATH = Path("/workspace/1-Raw Input Data/NPS/Untitled spreadsheet - US Parks.csv")
ENHANCED_DATA_PATH = Path("/workspace/2-Enhanced Data/NPS")

# Geocoding cache to avoid repeated API calls
GEOCODE_CACHE = {}
CACHE_FILE = Path("/workspace/src/spreadsheet_parser/geocode_cache.json")


def load_geocode_cache():
    """Load cached geocodes from file."""
    global GEOCODE_CACHE
    if CACHE_FILE.exists():
        with open(CACHE_FILE, 'r') as f:
            GEOCODE_CACHE = json.load(f)
    return GEOCODE_CACHE


def save_geocode_cache():
    """Save geocode cache to file."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(GEOCODE_CACHE, f, indent=2)


def geocode_address(address: str, city: str, state: str, zipcode: str) -> tuple:
    """
    Geocode an address using OpenStreetMap Nominatim API.
    Returns (lat, lon) tuple or (None, None) if not found.
    """
    # Build full address - only include non-empty parts
    parts = []
    if address and address.strip():
        parts.append(address.strip())
    if city and city.strip():
        parts.append(city.strip())
    if state and state.strip():
        parts.append(state.strip())
    if zipcode and zipcode.strip():
        parts.append(zipcode.strip())

    full_address = ", ".join(parts)

    if not full_address:
        return None, None

    # Check cache first
    cache_key = full_address.lower()
    if cache_key in GEOCODE_CACHE:
        cached = GEOCODE_CACHE[cache_key]
        return cached.get('lat'), cached.get('lon')

    # Rate limit: Nominatim requires 1 request per second
    time.sleep(1.1)

    try:
        # URL encode the address
        encoded_address = urllib.parse.quote(full_address)
        url = f"https://nominatim.openstreetmap.org/search?q={encoded_address}&format=json&limit=1"

        # Make request with proper User-Agent (required by Nominatim)
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'NPS-Trip-Planner/1.0 (research project)'}
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())

            if data and len(data) > 0:
                lat = round(float(data[0]['lat']), 6)
                lon = round(float(data[0]['lon']), 6)

                # Cache the result
                GEOCODE_CACHE[cache_key] = {'lat': lat, 'lon': lon}
                save_geocode_cache()

                return lat, lon
    except Exception as e:
        print(f"  Geocoding error for '{full_address}': {e}")

    # Cache the failure too (with None values)
    GEOCODE_CACHE[cache_key] = {'lat': None, 'lon': None}
    save_geocode_cache()

    return None, None


def format_hours(sun, mon, tue, wed, thu, fri, sat) -> str:
    """Format operating hours from day columns into a readable string."""
    days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    hours_list = [sun, mon, tue, wed, thu, fri, sat]

    # Clean up the values
    hours_list = [h.strip() if h else '' for h in hours_list]

    # Check if all are empty
    if not any(hours_list):
        return "Hours not available"

    # Check if all non-empty days are the same
    non_empty = [h for h in hours_list if h]
    unique_hours = set(non_empty)

    if len(unique_hours) == 1:
        hours = list(unique_hours)[0]
        if hours.lower() == 'open':
            return "Open 24 hours"
        elif hours.lower() == 'closed':
            return "Closed"
        return f"Daily: {hours}"

    # Check for weekday/weekend pattern
    weekday_hours = hours_list[1:6]  # Mon-Fri
    weekend_hours = [hours_list[0], hours_list[6]]  # Sun, Sat

    weekday_unique = set(h for h in weekday_hours if h)
    weekend_unique = set(h for h in weekend_hours if h)

    if len(weekday_unique) == 1 and len(weekend_unique) == 1:
        wd = list(weekday_unique)[0]
        we = list(weekend_unique)[0]
        if wd != we:
            return f"Mon-Fri: {wd}; Sat-Sun: {we}"
        else:
            return f"Daily: {wd}"

    # Otherwise build day-by-day, grouping consecutive same hours
    result = []
    i = 0
    while i < 7:
        if not hours_list[i]:
            i += 1
            continue

        start_day = days[i]
        current_hours = hours_list[i]
        j = i + 1

        while j < 7 and hours_list[j] == current_hours:
            j += 1

        end_day = days[j - 1]

        if start_day == end_day:
            result.append(f"{start_day}: {current_hours}")
        else:
            result.append(f"{start_day}-{end_day}: {current_hours}")

        i = j

    return "; ".join(result) if result else "Hours vary"


def normalize_park_name(name: str) -> str:
    """Normalize park name for directory matching."""
    if not name:
        return ""

    name = name.strip()

    # Handle & vs 'and'
    # The CSV uses & but directories may use 'and'
    return name


def find_matching_directory(park_name: str) -> Path:
    """Find the matching directory for a park name."""
    if not park_name:
        return None

    normalized = normalize_park_name(park_name)

    # Build list of variations to try
    variations = [
        normalized,
        normalized.replace("&", "and"),
        normalized.replace(" & ", " and "),
        normalized.replace(".", ""),
        normalized.replace("'", "'"),
    ]

    # Try exact matches first
    for var in variations:
        for dir_path in ENHANCED_DATA_PATH.iterdir():
            if dir_path.is_dir() and dir_path.name == var:
                return dir_path

    # Try case-insensitive match
    for var in variations:
        for dir_path in ENHANCED_DATA_PATH.iterdir():
            if dir_path.is_dir() and dir_path.name.lower() == var.lower():
                return dir_path

    # Try with different handling of special characters
    for var in variations:
        # Replace special chars with spaces for comparison
        var_clean = re.sub(r'[^\w\s]', ' ', var).lower()
        for dir_path in ENHANCED_DATA_PATH.iterdir():
            if dir_path.is_dir():
                dir_clean = re.sub(r'[^\w\s]', ' ', dir_path.name).lower()
                if dir_clean == var_clean:
                    return dir_path

    return None


def update_user_data_md(dir_path: Path, park_data: dict, vc_data: dict):
    """Update the user-data.md file with park and visitor center info."""
    user_data_path = dir_path / "user-data.md"

    if not user_data_path.exists():
        print(f"  No user-data.md found in {dir_path.name}")
        return False

    # Read existing content
    with open(user_data_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Build the new Amber's Data section
    ambers_data = "\n## Amber's Data (from spreadsheet)\n"

    # Visitor Center section (h3)
    if vc_data.get('name') or vc_data.get('address'):
        ambers_data += "\n### Visitor Center\n\n"
        if vc_data.get('name'):
            ambers_data += f"**Name:** {vc_data['name']}\n\n"

        if vc_data.get('address'):
            addr_parts = [vc_data['address']]
            if vc_data.get('city'):
                addr_parts.append(vc_data['city'])
            if vc_data.get('state'):
                addr_parts.append(vc_data['state'])
            if vc_data.get('zip'):
                addr_parts.append(vc_data['zip'])

            full_addr = ", ".join(p for p in addr_parts if p)

            if vc_data.get('lat') and vc_data.get('lon'):
                ambers_data += f"**Address:** {full_addr} ({vc_data['lat']}, {vc_data['lon']})\n\n"
            else:
                ambers_data += f"**Address:** {full_addr}\n\n"

        if vc_data.get('hours'):
            ambers_data += f"**Hours:** {vc_data['hours']}\n"

    # Park section (h3)
    if park_data.get('address'):
        ambers_data += "\n### Park\n\n"

        addr_parts = [park_data['address']]
        if park_data.get('city'):
            addr_parts.append(park_data['city'])
        if park_data.get('state'):
            addr_parts.append(park_data['state'])
        if park_data.get('zip'):
            addr_parts.append(park_data['zip'])

        full_addr = ", ".join(p for p in addr_parts if p)

        if park_data.get('lat') and park_data.get('lon'):
            ambers_data += f"**Address:** {full_addr} ({park_data['lat']}, {park_data['lon']})\n\n"
        else:
            ambers_data += f"**Address:** {full_addr}\n\n"

        if park_data.get('hours'):
            ambers_data += f"**Hours:** {park_data['hours']}\n"

    # Remove existing Amber's Data section if present
    # Use multiple patterns to catch different formats
    patterns = [
        r'\n## Amber\'s Data \(from spreadsheet\).*?(?=\n## Review|\Z)',
        r'\n## Amber\'s Data.*?(?=\n## Review|\Z)',
    ]

    for pattern in patterns:
        content = re.sub(pattern, '', content, flags=re.DOTALL)

    # Find where to insert - before "## Review / Personal Notes" or at end
    review_match = re.search(r'\n## Review / Personal Notes', content)

    if review_match:
        insert_pos = review_match.start()
        new_content = content[:insert_pos] + ambers_data + content[insert_pos:]
    else:
        # Add at end
        new_content = content.rstrip() + "\n" + ambers_data + "\n## Review / Personal Notes\n\n"

    # Write updated content
    with open(user_data_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return True


def parse_csv_and_update():
    """Main function to parse CSV and update all user-data.md files."""
    load_geocode_cache()

    print(f"Reading CSV from {CSV_PATH}")
    print(f"Geocode cache has {len(GEOCODE_CACHE)} entries")

    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)  # Skip header row

        print(f"CSV has {len(header)} columns")

        updated_count = 0
        not_found_count = 0
        no_userdata_count = 0

        for row_num, row in enumerate(reader, start=2):
            # Skip empty rows or state header rows
            if len(row) < 5 or not row[4] or row[4].strip() == '':
                continue

            park_name = row[4].strip() if len(row) > 4 else ''

            if not park_name:
                continue

            print(f"\n[{row_num}] Processing: {park_name}")

            # Skip bad data entries (malformed entries with semicolons)
            normalized = normalize_name(park_name)
            if ";" in normalized and "memorial parks" in normalized:
                print(f"  Skipping malformed entry: {park_name}")
                continue

            # Find matching directory using name_mapping module
            if not directory_exists(park_name):
                print(f"  Directory not found for: {park_name}")
                not_found_count += 1
                continue

            dir_path = get_directory_path(park_name)
            print(f"  Found directory: {dir_path.name}")

            # Extract park data (columns 5-8 for address, 9-15 for hours)
            park_address = row[5].strip() if len(row) > 5 else ''
            park_city = row[6].strip() if len(row) > 6 else ''
            park_state = row[7].strip() if len(row) > 7 else ''
            park_zip = row[8].strip() if len(row) > 8 else ''

            # Park hours: columns 9-15 (Sun-Sat)
            park_sun = row[9].strip() if len(row) > 9 else ''
            park_mon = row[10].strip() if len(row) > 10 else ''
            park_tue = row[11].strip() if len(row) > 11 else ''
            park_wed = row[12].strip() if len(row) > 12 else ''
            park_thu = row[13].strip() if len(row) > 13 else ''
            park_fri = row[14].strip() if len(row) > 14 else ''
            park_sat = row[15].strip() if len(row) > 15 else ''

            # Extract visitor center data (columns 17-21 for address, 22-28 for hours)
            vc_name = row[17].strip() if len(row) > 17 else ''
            vc_address = row[18].strip() if len(row) > 18 else ''
            vc_city = row[19].strip() if len(row) > 19 else ''
            vc_state = row[20].strip() if len(row) > 20 else ''
            vc_zip = row[21].strip() if len(row) > 21 else ''

            # VC hours: columns 22-28 (Sun-Sat)
            vc_sun = row[22].strip() if len(row) > 22 else ''
            vc_mon = row[23].strip() if len(row) > 23 else ''
            vc_tue = row[24].strip() if len(row) > 24 else ''
            vc_wed = row[25].strip() if len(row) > 25 else ''
            vc_thu = row[26].strip() if len(row) > 26 else ''
            vc_fri = row[27].strip() if len(row) > 27 else ''
            vc_sat = row[28].strip() if len(row) > 28 else ''

            # Format hours
            park_hours = format_hours(park_sun, park_mon, park_tue, park_wed, park_thu, park_fri, park_sat)
            vc_hours = format_hours(vc_sun, vc_mon, vc_tue, vc_wed, vc_thu, vc_fri, vc_sat)

            # Geocode addresses
            print(f"  Geocoding park: {park_address}, {park_city}, {park_state}")
            park_lat, park_lon = geocode_address(park_address, park_city, park_state, park_zip)
            if park_lat:
                print(f"    -> ({park_lat}, {park_lon})")

            print(f"  Geocoding VC: {vc_address}, {vc_city}, {vc_state}")
            vc_lat, vc_lon = geocode_address(vc_address, vc_city, vc_state, vc_zip)
            if vc_lat:
                print(f"    -> ({vc_lat}, {vc_lon})")

            # Build data dictionaries
            park_data = {
                'address': park_address,
                'city': park_city,
                'state': park_state,
                'zip': park_zip,
                'hours': park_hours,
                'lat': park_lat,
                'lon': park_lon
            }

            vc_data = {
                'name': vc_name,
                'address': vc_address,
                'city': vc_city,
                'state': vc_state,
                'zip': vc_zip,
                'hours': vc_hours,
                'lat': vc_lat,
                'lon': vc_lon
            }

            # Update user-data.md
            if update_user_data_md(dir_path, park_data, vc_data):
                print(f"  Updated user-data.md")
                updated_count += 1
            else:
                print(f"  Failed to update user-data.md")
                no_userdata_count += 1

    print(f"\n\n{'='*50}")
    print(f"Summary:")
    print(f"  Updated: {updated_count}")
    print(f"  Directory not found: {not_found_count}")
    print(f"  No user-data.md: {no_userdata_count}")
    print(f"  Geocode cache size: {len(GEOCODE_CACHE)}")


if __name__ == "__main__":
    parse_csv_and_update()
