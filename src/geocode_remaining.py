#!/usr/bin/env python3
"""
Geocode all remaining addresses in ambers-data.md files that don't have coordinates
"""
import json
import re
import time
from pathlib import Path
from typing import Dict, Tuple, Optional
import requests


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
        print(f"    Error: {e}")

    return None


def geocode_all_missing(base_dir: Path, geocode_cache: Dict):
    """Find and geocode all addresses without coordinates"""

    print(f"Scanning: {base_dir}")
    print(f"Initial cache size: {len(geocode_cache)}")
    print()

    geocoded_count = 0
    failed_count = 0
    updated_files = []

    for site_dir in sorted(base_dir.iterdir()):
        if not site_dir.is_dir():
            continue

        ambers_file = site_dir / "ambers-data.md"
        if not ambers_file.exists():
            continue

        content = ambers_file.read_text()

        # Check if address has geocode
        # Pattern: **Address:** ... (lat, lon)
        addr_match = re.search(r'\*\*Address:\*\*\s*(.+?)(?:\s*\((-?\d+\.?\d*),\s*(-?\d+\.?\d*)\))?$', content, re.MULTILINE)

        if not addr_match:
            continue

        address = addr_match.group(1).strip()
        lat_str = addr_match.group(2)
        lon_str = addr_match.group(3)

        # Skip if already has geocode
        if lat_str and lon_str:
            continue

        # Skip if no address
        if not address or address.lower() == 'not available':
            continue

        print(f"  🌍 {site_dir.name}")
        print(f"     Address: {address}")

        # Check cache first
        lat, lon = None, None

        if address in geocode_cache:
            lat, lon = geocode_cache[address]
            print(f"     ✓ Found in cache: ({lat}, {lon})")
        else:
            # Try partial match
            for cached_addr, coords in geocode_cache.items():
                if address in cached_addr or cached_addr in address:
                    lat, lon = coords
                    print(f"     ✓ Found partial match in cache: ({lat}, {lon})")
                    break

            # Geocode if not in cache
            if not lat or not lon:
                coords = geocode_address(address)

                if coords:
                    lat, lon = coords
                    geocode_cache[address] = coords
                    geocoded_count += 1
                    print(f"     ✓ Geocoded: ({lat}, {lon})")
                    time.sleep(1)  # Rate limit
                else:
                    failed_count += 1
                    print(f"     ✗ Failed to geocode")
                    continue

        # Update the file with geocode
        if lat and lon:
            # Replace address line with geocoded version
            new_line = f"**Address:** {address} ({lat}, {lon})"
            old_line = f"**Address:** {address}"

            new_content = content.replace(old_line, new_line)

            if new_content != content:
                ambers_file.write_text(new_content)
                updated_files.append(site_dir.name)
                print(f"     ✓ Updated file")

    # Save cache
    save_geocode_cache(geocode_cache)

    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"Files updated: {len(updated_files)}")
    print(f"New geocodes: {geocoded_count}")
    print(f"Failed: {failed_count}")
    print(f"Final cache size: {len(geocode_cache)}")


def main():
    """Main entry point"""
    base_dir = Path("2-Enhanced Data/NPS")

    if not base_dir.exists():
        print(f"Error: Base directory not found at {base_dir}")
        return

    # Load cache
    geocode_cache = load_geocode_cache()

    # Geocode all missing
    geocode_all_missing(base_dir, geocode_cache)


if __name__ == '__main__':
    main()
