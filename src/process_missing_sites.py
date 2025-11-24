#!/usr/bin/env python3
"""
Process missing NPS sites:
1. Create directories for sites not found
2. Geocode missing addresses
3. Create ambers-data.md files
"""
import csv
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import requests


def normalize_name(name: str) -> str:
    """Normalize park name to match normalize_nps_names.py"""
    import re

    name = name.strip()
    name = name.replace(' & ', ' and ')
    name = name.replace('/', ' ')
    name = name.replace('_', ' ')
    name = re.sub(r'\.(?=\s|$)', '', name)
    name = name.replace('\u2019', "'")
    name = re.sub(r'\s+', ' ', name)
    name = re.sub(r'[^\w\s\-\'(),]', '', name)

    return name.strip()


def load_geocode_cache() -> Dict[str, Tuple[float, float]]:
    """Load existing geocode cache"""
    cache_file = Path("geocode_cache.json")
    if cache_file.exists():
        with open(cache_file) as f:
            cache = json.load(f)
            return {
                addr: (coords[0], coords[1])
                for addr, coords in cache.items()
                if isinstance(coords, list) and len(coords) == 2
            }
    return {}


def save_geocode_cache(cache: Dict[str, Tuple[float, float]]):
    """Save geocode cache"""
    cache_file = Path("geocode_cache.json")
    # Convert to [lat, lon] format
    output = {addr: [lat, lon] for addr, (lat, lon) in cache.items()}
    with open(cache_file, 'w') as f:
        json.dump(output, f, indent=2)


def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    """Geocode an address using Nominatim"""
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': address,
        'format': 'json',
        'limit': 1
    }
    headers = {
        'User-Agent': 'NPS-Site-Mapper/1.0'
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        results = response.json()

        if results:
            lat = float(results[0]['lat'])
            lon = float(results[0]['lon'])
            return (lat, lon)
    except Exception as e:
        print(f"    Error geocoding: {e}")

    return None


def normalize_address(address: str, city: str, state: str, zip_code: str) -> str:
    """Create normalized address string"""
    addr = address.strip().rstrip(',').strip()
    city = city.strip()
    state = state.strip()
    zip_code = zip_code.strip()

    if zip_code:
        return f"{addr}, {city}, {state} {zip_code}"
    else:
        return f"{addr}, {city}, {state}"


def parse_hours(hours_cols: list) -> str:
    """Parse operating hours from CSV columns (Sun-Sat)"""
    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

    unique_hours = set(h.strip() for h in hours_cols if h.strip() and h.strip().lower() != 'closed')

    if not unique_hours:
        return "Closed"

    if len(unique_hours) == 1:
        hours = list(unique_hours)[0]
        open_days = [days[i] for i, h in enumerate(hours_cols) if h.strip() and h.strip().lower() != 'closed']

        if len(open_days) == 7:
            return f"Daily: {hours}"
        elif len(open_days) >= 5:
            return f"{hours} (check website for specific days)"
        else:
            return f"{', '.join(open_days)}: {hours}"
    else:
        return "Varies by day (check website)"


def process_missing_sites(csv_file: Path, base_dir: Path, geocode_cache: Dict):
    """Process all missing sites from CSV"""

    print(f"Reading CSV: {csv_file}")
    print(f"Base directory: {base_dir}")
    print(f"Initial geocode cache entries: {len(geocode_cache)}")
    print()

    created_count = 0
    geocoded_count = 0
    missing_sites = []

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header

        for row in reader:
            if len(row) < 29:
                continue

            park_name = row[4].strip()
            if not park_name:
                continue

            # Normalize the park name
            normalized_name = normalize_name(park_name)
            site_dir = base_dir / normalized_name

            # Only process if directory doesn't exist
            if site_dir.exists():
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
                print(f"  ✗ No address for: {park_name}")
                missing_sites.append(park_name)
                continue

            # Normalize address
            full_address = normalize_address(vc_address, vc_city, vc_state, vc_zip)

            # Look up or geocode
            lat, lon = None, None

            if full_address in geocode_cache:
                lat, lon = geocode_cache[full_address]
                print(f"  ✓ Using cached geocode: {park_name}")
            else:
                # Try partial match
                addr_no_zip = normalize_address(vc_address, vc_city, vc_state, "")
                for cached_addr, coords in geocode_cache.items():
                    if addr_no_zip in cached_addr or cached_addr in addr_no_zip:
                        lat, lon = coords
                        print(f"  ✓ Using cached geocode (partial): {park_name}")
                        break

                # Geocode if not found
                if not lat or not lon:
                    print(f"  🌍 Geocoding: {park_name}")
                    print(f"     Address: {full_address}")
                    coords = geocode_address(full_address)

                    if coords:
                        lat, lon = coords
                        geocode_cache[full_address] = coords
                        geocoded_count += 1
                        print(f"     ✓ Geocoded: ({lat}, {lon})")
                        # Rate limit
                        time.sleep(1)
                    else:
                        print(f"     ✗ Failed to geocode")

            # Parse hours
            vc_hours_cols = [row[22], row[23], row[24], row[25], row[26], row[27], row[28]]
            hours_str = parse_hours(vc_hours_cols)

            # Create directory
            site_dir.mkdir(parents=True, exist_ok=True)
            print(f"  📁 Created directory: {normalized_name}")

            # Create ambers-data.md
            content = f"# Amber's Data\n\n"
            content += f"**Visitor Center:** {vc_location}\n\n"

            if lat and lon:
                content += f"**Address:** {full_address} ({lat}, {lon})\n\n"
            else:
                content += f"**Address:** {full_address}\n\n"

            content += f"**Hours:** {hours_str}\n"

            ambers_file = site_dir / "ambers-data.md"
            ambers_file.write_text(content)

            created_count += 1

            if created_count % 10 == 0:
                print(f"\n  ... processed {created_count} sites\n")

    # Save updated geocode cache
    save_geocode_cache(geocode_cache)

    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"Directories created: {created_count}")
    print(f"New geocodes: {geocoded_count}")
    print(f"Sites without addresses: {len(missing_sites)}")
    print(f"Total geocode cache entries: {len(geocode_cache)}")

    if missing_sites:
        print(f"\nSites without addresses:")
        for site in missing_sites:
            print(f"  - {site}")


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

    # Process missing sites
    process_missing_sites(csv_file, base_dir, geocode_cache)


if __name__ == '__main__':
    main()
