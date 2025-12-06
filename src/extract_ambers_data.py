#!/usr/bin/env python3
"""
Extract Amber's Data sections from NPS site files and create separate ambers-data.md files.
- Finds all "Amber's Data" sections in user-data.md or main site files
- Extracts the content
- Creates ambers-data.md files
- Geocodes any addresses that aren't geocoded
- Removes hash values in square brackets
"""
import re
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Optional, Tuple


# Geocode cache
GEOCODE_CACHE_FILE = Path("/workspace/geocode_cache.json")


def load_geocode_cache() -> Dict:
    """Load existing geocode cache"""
    if GEOCODE_CACHE_FILE.exists():
        with open(GEOCODE_CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_geocode_cache(cache: Dict):
    """Save geocode cache"""
    with open(GEOCODE_CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)


def geocode_address(address: str, cache: Dict) -> Optional[Tuple[float, float]]:
    """Geocode an address using Nominatim (with caching)"""
    # Clean address for lookup
    clean_address = re.sub(r'\s*\([^)]*\)\s*$', '', address).strip()

    if clean_address in cache:
        coords = cache[clean_address]
        if coords:
            return tuple(coords)
        return None

    try:
        url = f"https://nominatim.openstreetmap.org/search?{urllib.parse.urlencode({'q': clean_address, 'format': 'json', 'limit': 1})}"
        req = urllib.request.Request(url, headers={'User-Agent': 'NPS-Data-Processor/1.0'})

        with urllib.request.urlopen(req, timeout=10.0) as response:
            data = json.loads(response.read().decode())

            if data:
                coords = (float(data[0]['lat']), float(data[0]['lon']))
                cache[clean_address] = list(coords)
                save_geocode_cache(cache)
                time.sleep(1.1)  # Rate limiting
                return coords
            else:
                cache[clean_address] = None
                save_geocode_cache(cache)

    except Exception as e:
        print(f"    ⚠ Geocoding error for {clean_address}: {e}")
        cache[clean_address] = None
        save_geocode_cache(cache)

    return None


def remove_hash_values(text: str) -> str:
    """Remove hash values in square brackets like [ff436f], [942cba], etc."""
    # Pattern matches square brackets containing hex values (6 characters)
    pattern = r'\s*\[([0-9a-fA-F]{6})\]'
    return re.sub(pattern, '', text)


def extract_ambers_data(file_path: Path, geocode_cache: Dict) -> Optional[str]:
    """Extract Amber's Data section from a file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find Amber's Data section
    pattern = r"##\s*Amber'?s\s+Data[^\n]*\n(.*?)(?=##|\Z)"
    match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)

    if not match:
        return None

    ambers_data = match.group(1).strip()

    # Remove hash values
    ambers_data = remove_hash_values(ambers_data)

    # Find addresses that need geocoding
    # Pattern: **Address:** some address (without coordinates already)
    address_pattern = r'\*\*Address:\*\*\s+([^\n(]+?)(?:\n|$)'

    def replace_address(match):
        address = match.group(1).strip()

        # Check if already geocoded (has coordinates in parentheses)
        if re.search(r'\(\s*-?\d+\.?\d*\s*,\s*-?\d+\.?\d*\s*\)', address):
            return match.group(0)

        # Need to geocode
        return match.group(0)  # Will process later

    # First pass: identify addresses
    addresses_to_geocode = []
    for match in re.finditer(address_pattern, ambers_data):
        address = match.group(1).strip()
        # Check if already geocoded
        if not re.search(r'\(\s*-?\d+\.?\d*\s*,\s*-?\d+\.?\d*\s*\)', address):
            addresses_to_geocode.append(address)

    # Geocode addresses
    geocoded_addresses = {}
    for address in addresses_to_geocode:
        coords = geocode_address(address, geocode_cache)
        if coords:
            geocoded_addresses[address] = coords

    # Second pass: replace addresses with geocoded versions
    def replace_with_geocode(match):
        address = match.group(1).strip()
        if address in geocoded_addresses:
            coords = geocoded_addresses[address]
            return f"**Address:** {address} ({coords[0]}, {coords[1]})"
        return match.group(0)

    ambers_data = re.sub(address_pattern, replace_with_geocode, ambers_data)

    return ambers_data


def process_site_directory(site_dir: Path, geocode_cache: Dict, stats: Dict):
    """Process a single site directory"""
    site_name = site_dir.name

    # Check if ambers-data.md already exists
    ambers_file = site_dir / "ambers-data.md"
    if ambers_file.exists():
        print(f"  ℹ ambers-data.md already exists")
        stats['skipped'] += 1
        return

    # Look for Amber's Data in user-data.md first
    user_data_file = site_dir / "user-data.md"
    ambers_data = None

    if user_data_file.exists():
        ambers_data = extract_ambers_data(user_data_file, geocode_cache)

    # If not found, look in main site file
    if not ambers_data:
        # Find the main site file (any .md file that's not user-data.md or ambers-data.md)
        for md_file in site_dir.glob("*.md"):
            if md_file.name not in ['user-data.md', 'ambers-data.md']:
                ambers_data = extract_ambers_data(md_file, geocode_cache)
                if ambers_data:
                    break

    if ambers_data:
        # Create ambers-data.md file
        with open(ambers_file, 'w', encoding='utf-8') as f:
            f.write("# Amber's Data\n\n")
            f.write(ambers_data)
            f.write("\n")

        print(f"  ✓ Created ambers-data.md")
        stats['created'] += 1

        # Count geocoded addresses
        geocode_count = len(re.findall(r'\(\s*-?\d+\.?\d*\s*,\s*-?\d+\.?\d*\s*\)', ambers_data))
        stats['geocoded'] += geocode_count
    else:
        print(f"  - No Amber's Data found")
        stats['no_data'] += 1


def main():
    """Main processing function"""
    print("="*80)
    print("Extracting Amber's Data from NPS Site Files")
    print("="*80)

    # Load geocode cache
    print("\nLoading geocode cache...")
    geocode_cache = load_geocode_cache()
    print(f"✓ Loaded {len(geocode_cache)} cached geocodes")

    # Find all NPS site directories
    nps_dir = Path("/workspace/2-Enhanced Data/NPS")
    if not nps_dir.exists():
        print(f"Error: NPS directory not found at {nps_dir}")
        return

    site_dirs = [d for d in nps_dir.iterdir() if d.is_dir()]
    print(f"✓ Found {len(site_dirs)} site directories")

    # Process each site
    print("\nProcessing sites...")
    print("-" * 80)

    stats = {
        'created': 0,
        'skipped': 0,
        'no_data': 0,
        'geocoded': 0,
        'errors': 0
    }

    for site_dir in sorted(site_dirs):
        print(f"\n{site_dir.name}")
        try:
            process_site_directory(site_dir, geocode_cache, stats)
        except Exception as e:
            print(f"  ✗ Error: {e}")
            stats['errors'] += 1

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"✓ Created ambers-data.md files: {stats['created']}")
    print(f"⊘ Already existed (skipped): {stats['skipped']}")
    print(f"- No Amber's Data found: {stats['no_data']}")
    print(f"✗ Errors encountered: {stats['errors']}")
    print(f"📍 Addresses geocoded in this run: {stats['geocoded']}")
    print(f"📍 Total geocodes in cache: {len(geocode_cache)}")
    print("\nGeocodes saved to: geocode_cache.json")


if __name__ == '__main__':
    main()
