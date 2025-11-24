#!/usr/bin/env python3
"""
Populate ambers-data.md files from raw CSV input
Extracts visitor center locations and operating hours
"""
import csv
import json
import re
from pathlib import Path
from typing import Dict, Optional, Tuple


def load_geocode_cache() -> Dict[str, Tuple[float, float]]:
    """Load geocode cache from JSON file"""
    cache_file = Path("geocode_cache.json")
    if cache_file.exists():
        with open(cache_file) as f:
            cache = json.load(f)
            # Convert to dict of address -> (lat, lon)
            # Cache format: {"address": [lat, lon]}
            return {
                addr: (coords[0], coords[1])
                for addr, coords in cache.items()
                if isinstance(coords, list) and len(coords) == 2
            }
    return {}


def normalize_address(address: str, city: str, state: str, zip_code: str) -> str:
    """Create normalized address string"""
    # Clean up address
    addr = address.strip().rstrip(',').strip()
    city = city.strip()
    state = state.strip()
    zip_code = zip_code.strip()

    if zip_code:
        return f"{addr}, {city}, {state} {zip_code}"
    else:
        return f"{addr}, {city}, {state}"


def find_site_directory(park_name: str, base_dir: Path) -> Optional[Path]:
    """Find the directory for a given park name"""
    # Try exact match first
    site_dir = base_dir / park_name
    if site_dir.exists():
        return site_dir

    # Try case-insensitive and partial matches
    for dir_path in base_dir.iterdir():
        if not dir_path.is_dir():
            continue

        # Exact match (case-insensitive)
        if dir_path.name.lower() == park_name.lower():
            return dir_path

        # Partial match (park name is in directory name)
        if park_name.lower() in dir_path.name.lower():
            return dir_path

    return None


def parse_hours(hours_cols: list) -> str:
    """Parse operating hours from CSV columns (Sun-Sat)"""
    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

    # Check if all days are the same
    unique_hours = set(h.strip() for h in hours_cols if h.strip() and h.strip().lower() != 'closed')

    if not unique_hours:
        return "Closed"

    if len(unique_hours) == 1:
        # All open days have same hours
        hours = list(unique_hours)[0]

        # Count which days are open
        open_days = [days[i] for i, h in enumerate(hours_cols) if h.strip() and h.strip().lower() != 'closed']

        if len(open_days) == 7:
            return f"Daily: {hours}"
        elif len(open_days) >= 5:
            return f"{hours} (check website for specific days)"
        else:
            return f"{', '.join(open_days)}: {hours}"
    else:
        # Different hours on different days
        return "Varies by day (check website)"


def update_ambers_data(csv_file: Path, base_dir: Path, geocode_cache: Dict):
    """Update all ambers-data.md files from CSV"""

    print(f"Reading CSV: {csv_file}")
    print(f"Base directory: {base_dir}")
    print(f"Geocode cache entries: {len(geocode_cache)}")

    updated_count = 0
    not_found_count = 0
    missing_geocode = []

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        # Skip header
        header = next(reader)

        # Column indices based on raw CSV
        # 4: National Park, 5: Address, 6: City, 7: State, 8: Zip
        # 17: VC Location, 18: VC Address, 19: VC City, 20: VC State, 21: VC Zip
        # 22-28: VC Hours (Sunday-Saturday)

        for row in reader:
            if len(row) < 29:  # Skip incomplete rows
                continue

            park_name = row[4].strip()
            if not park_name:
                continue

            # Find the site directory
            site_dir = find_site_directory(park_name, base_dir)
            if not site_dir:
                print(f"  ✗ Directory not found: {park_name}")
                not_found_count += 1
                continue

            # Extract visitor center info
            vc_location = row[17].strip()
            vc_address = row[18].strip()
            vc_city = row[19].strip()
            vc_state = row[20].strip()
            vc_zip = row[21].strip()

            # If no visitor center info, use park info
            if not vc_location and not vc_address:
                vc_location = f"{park_name} Visitor Center"
                vc_address = row[5].strip()
                vc_city = row[6].strip()
                vc_state = row[7].strip()
                vc_zip = row[8].strip()

            if not vc_address:
                print(f"  ✗ No address: {park_name}")
                not_found_count += 1
                continue

            # Normalize address
            full_address = normalize_address(vc_address, vc_city, vc_state, vc_zip)

            # Look up geocode
            lat, lon = None, None

            # Try exact match
            if full_address in geocode_cache:
                lat, lon = geocode_cache[full_address]
            else:
                # Try partial matches (address without zip)
                addr_no_zip = normalize_address(vc_address, vc_city, vc_state, "")
                for cached_addr, coords in geocode_cache.items():
                    if addr_no_zip in cached_addr or cached_addr in addr_no_zip:
                        lat, lon = coords
                        break

            if not lat or not lon:
                missing_geocode.append((park_name, full_address))

            # Parse hours (visitor center hours columns 22-28)
            vc_hours_cols = [row[22], row[23], row[24], row[25], row[26], row[27], row[28]]

            hours_str = parse_hours(vc_hours_cols)

            # Create ambers-data.md content
            content = f"# Amber's Data\n\n"
            content += f"**Visitor Center:** {vc_location}\n\n"

            if lat and lon:
                content += f"**Address:** {full_address} ({lat}, {lon})\n\n"
            else:
                content += f"**Address:** {full_address}\n\n"

            content += f"**Hours:** {hours_str}\n"

            # Write to file
            ambers_file = site_dir / "ambers-data.md"
            ambers_file.write_text(content)

            updated_count += 1
            if updated_count % 50 == 0:
                print(f"  ... processed {updated_count} sites")

    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"Updated: {updated_count}")
    print(f"Not found: {not_found_count}")
    print(f"Missing geocodes: {len(missing_geocode)}")

    if missing_geocode:
        print(f"\nSites needing geocoding:")
        for park, addr in missing_geocode[:10]:
            print(f"  - {park}: {addr}")
        if len(missing_geocode) > 10:
            print(f"  ... and {len(missing_geocode) - 10} more")


def main():
    """Main entry point"""
    csv_file = Path("1-Raw Input Data/NPS/Untitled spreadsheet - US Parks.csv")
    base_dir = Path("2-Enhanced Data/NPS")

    if not csv_file.exists():
        print(f"Error: CSV file not found at {csv_file}")
        return

    if not base_dir.exists():
        print(f"Error: Base directory not found at {base_dir}")
        return

    # Load geocode cache
    geocode_cache = load_geocode_cache()

    # Update all files
    update_ambers_data(csv_file, base_dir, geocode_cache)


if __name__ == '__main__':
    main()
