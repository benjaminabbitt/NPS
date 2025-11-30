#!/usr/bin/env python3
"""
Add geocode coordinates to all addresses in ALL NPS site markdown files.
Uses existing geocode cache and Chroma database, geocodes new addresses via Nominatim.
"""

import json
import re
import asyncio
import httpx
import urllib.parse
from pathlib import Path
from typing import Optional, Tuple, Dict, List
import time

# State abbreviation mappings
STATE_ABBREVS = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR',
    'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
    'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID',
    'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS',
    'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
    'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS',
    'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV',
    'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY',
    'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK',
    'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
    'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT',
    'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV',
    'Wisconsin': 'WI', 'Wyoming': 'WY', 'District of Columbia': 'DC'
}

# Reverse mapping
ABBREV_TO_STATE = {v: k for k, v in STATE_ABBREVS.items()}


def normalize_address(addr: str) -> str:
    """Normalize address for cache lookup - standardize format"""
    addr = addr.strip()

    # Convert "City, ST Zip" to "City, State, Zip" for cache lookup
    # Caches use full state names like "Nebraska, 69346"
    for abbrev, state in ABBREV_TO_STATE.items():
        # Match ', ST 12345' pattern (with space between state and zip)
        pattern = rf',\s*{abbrev}\s+(\d{{5}})'
        addr = re.sub(pattern, f', {state}, \\1', addr)

    return addr


def load_geocode_cache(cache_file: Path) -> Dict:
    """Load existing geocode cache"""
    if cache_file.exists():
        with open(cache_file, 'r') as f:
            return json.load(f)
    return {}


def load_chroma_geocodes(use_cache: bool = True) -> Dict:
    """Load geocodes from Chroma database, with optional file caching"""
    cache_file = Path('chroma_geocodes_cache.json')

    # Try to load from file cache first
    if use_cache and cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            print(f"  (loaded from cache file)")
            return data
        except Exception:
            pass

    # Load from Chroma
    try:
        import chromadb
        client = chromadb.PersistentClient(path='./chroma.db')
        geocodes = client.get_collection('nps_geocodes')

        results = geocodes.get(include=['metadatas'])
        chroma_cache = {}

        for meta in results['metadatas']:
            addr = meta.get('address', '')
            lat = meta.get('latitude')
            lon = meta.get('longitude')
            if addr and lat and lon:
                chroma_cache[addr] = [lat, lon]

        # Save to file cache
        with open(cache_file, 'w') as f:
            json.dump(chroma_cache, f, indent=2)

        return chroma_cache
    except Exception as e:
        print(f"Warning: Could not load Chroma geocodes: {e}")
        return {}


def save_geocode_cache(cache: Dict, cache_file: Path):
    """Save geocode cache"""
    with open(cache_file, 'w') as f:
        json.dump(cache, f, indent=2)


def lookup_geocode(address: str, cache: Dict, chroma_cache: Dict) -> Optional[Tuple[float, float]]:
    """
    Look up geocode from caches using multiple address formats.
    Returns coordinates if found, None otherwise.
    """
    # Try exact match first
    for lookup_addr in [address, normalize_address(address)]:
        if lookup_addr in cache:
            coords = cache[lookup_addr]
            if coords and isinstance(coords, (list, tuple)) and len(coords) == 2:
                return tuple(coords)

        if lookup_addr in chroma_cache:
            coords = chroma_cache[lookup_addr]
            if coords and isinstance(coords, (list, tuple)) and len(coords) == 2:
                return tuple(coords)

    return None


async def geocode_address(
    address: str,
    cache: Dict,
    chroma_cache: Dict,
    client: httpx.AsyncClient,
    new_geocode_count: list  # Mutable container for counting
) -> Optional[Tuple[float, float]]:
    """Geocode an address, using caches first, then Nominatim"""
    # Try cache lookups first
    coords = lookup_geocode(address, cache, chroma_cache)
    if coords:
        return coords

    # Geocode using Nominatim (rate limited)
    try:
        url = f"https://nominatim.openstreetmap.org/search?{urllib.parse.urlencode({'q': address, 'format': 'json', 'limit': 1})}"
        headers = {'User-Agent': 'NPS-Geocoder/1.0'}

        response = await client.get(url, headers=headers, timeout=10.0)
        data = response.json()

        if data:
            coords = (float(data[0]['lat']), float(data[0]['lon']))
            cache[address] = list(coords)
            new_geocode_count[0] += 1
            await asyncio.sleep(1.1)  # Rate limiting for Nominatim
            return coords
    except Exception as e:
        print(f"    Error geocoding '{address[:50]}...': {e}")

    return None


def extract_address_from_parentheses(text: str) -> Optional[str]:
    """Extract just the address part (before first semicolon)"""
    # Remove leading parenthesis
    text = text.lstrip('(')
    # Get everything before first semicolon
    parts = text.split(';')
    address = parts[0].strip()

    # Skip if it's not a real address
    if len(address) < 10:
        return None
    # Skip if it looks like coordinates already
    if re.search(r'^\s*-?\d+\.\d+\s*,\s*-?\d+\.\d+', address):
        return None
    # Skip if it looks like time/duration
    if re.search(r'\d+\s*(hour|minute|min|hr)', address.lower()):
        return None
    # Skip if it doesn't seem to have geographic info
    if not re.search(r'(street|st|road|rd|avenue|ave|drive|dr|blvd|highway|hwy|route|way|\d{5}|[A-Z]{2}\s+\d{5})', address, re.I):
        return None

    return address


def has_geocode_already(text: str) -> bool:
    """Check if text already contains geocode coordinates"""
    # Match patterns like (38.123, -90.456) within address
    return bool(re.search(r'\(\s*-?\d+\.\d+\s*,\s*-?\d+\.\d+\s*\)', text))


async def process_markdown_file(
    md_file: Path,
    geocode_cache: Dict,
    chroma_cache: Dict,
    client: httpx.AsyncClient,
    new_geocode_count: list,
    dry_run: bool = False
) -> Tuple[int, int]:
    """
    Process a single markdown file to add geocodes.
    Returns (addresses_found, addresses_geocoded)
    """
    content = md_file.read_text(encoding='utf-8')
    original_content = content

    # Pattern to find addresses in format: (address; hours; phone) or (address)
    # This matches content in parentheses that contains semicolons OR looks like an address
    pattern = r'\(([^()]+(?:;[^()]+)*)\)'

    matches = list(re.finditer(pattern, content))
    addresses_found = 0
    addresses_geocoded = 0

    for match in reversed(matches):  # Process in reverse to maintain positions
        full_match = match.group(0)
        inner_content = match.group(1)

        # Skip if already has geocode
        if has_geocode_already(full_match):
            continue

        # Extract the address
        address = extract_address_from_parentheses(full_match)
        if not address:
            continue

        addresses_found += 1

        # Geocode the address
        coords = await geocode_address(address, geocode_cache, chroma_cache, client, new_geocode_count)

        if coords:
            # Format: (address (lat, lon); hours; phone)
            # Insert coordinates after address but before semicolon
            if ';' in inner_content:
                parts = inner_content.split(';', 1)
                new_content = f"({parts[0].strip()} ({coords[0]}, {coords[1]}); {parts[1].strip()})"
            else:
                # Just address, no semicolons
                new_content = f"({inner_content.strip()} ({coords[0]}, {coords[1]}))"

            content = content[:match.start()] + new_content + content[match.end():]
            addresses_geocoded += 1
            print(f"    + Geocoded: {address[:50]}... -> ({coords[0]}, {coords[1]})")

    if not dry_run and content != original_content:
        md_file.write_text(content, encoding='utf-8')

    return addresses_found, addresses_geocoded


async def process_all_sites(base_path: Path, geocode_cache: Dict, chroma_cache: Dict, dry_run: bool = False) -> Dict:
    """Process all NPS sites"""
    results = {
        'sites_processed': 0,
        'sites_updated': 0,
        'total_addresses': 0,
        'total_geocoded': 0,
        'new_geocodes': 0,
        'errors': []
    }

    new_geocode_count = [0]  # Mutable counter for new Nominatim lookups

    async with httpx.AsyncClient() as client:
        # Get all site directories
        site_dirs = sorted([d for d in base_path.iterdir() if d.is_dir()])

        for site_dir in site_dirs:
            site_name = site_dir.name

            # Skip non-site directories
            if site_name.startswith('.') or site_name == 'CLAUDE.md':
                continue

            # Find markdown files
            md_files = list(site_dir.glob('*.md'))

            for md_file in md_files:
                # Skip ambers-data and CLAUDE files
                if md_file.name in ('ambers-data.md', 'CLAUDE.md'):
                    continue

                try:
                    found, geocoded = await process_markdown_file(
                        md_file, geocode_cache, chroma_cache, client, new_geocode_count, dry_run
                    )

                    if found > 0:
                        results['sites_processed'] += 1
                        results['total_addresses'] += found
                        results['total_geocoded'] += geocoded

                        if geocoded > 0:
                            results['sites_updated'] += 1
                            print(f"  {site_name}/{md_file.name}: {geocoded}/{found} addresses geocoded")

                except Exception as e:
                    results['errors'].append(f"{site_name}/{md_file.name}: {e}")
                    print(f"  ERROR: {site_name}/{md_file.name}: {e}")

    results['new_geocodes'] = new_geocode_count[0]
    return results


async def main():
    """Main execution"""
    import argparse

    parser = argparse.ArgumentParser(description='Add geocodes to all NPS sites')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be geocoded without making changes')
    parser.add_argument('--limit', type=int, default=0,
                        help='Limit number of new geocodes (for testing)')
    args = parser.parse_args()

    print("=" * 70)
    print("NPS Site Geocoding - All Sites")
    print("=" * 70)

    base_path = Path('2-Enhanced Data/NPS')
    cache_file = Path('geocode_cache.json')

    if not base_path.exists():
        print(f"Error: Base path not found: {base_path}")
        return

    # Load geocode caches
    geocode_cache = load_geocode_cache(cache_file)
    initial_cache_size = len(geocode_cache)
    print(f"\nLoaded {initial_cache_size} cached geocodes from file")

    chroma_cache = load_chroma_geocodes()
    print(f"Loaded {len(chroma_cache)} geocodes from Chroma database")

    if args.dry_run:
        print("\n*** DRY RUN MODE - No changes will be made ***\n")
    else:
        print("\n*** PROCESSING FILES ***\n")

    # Process all sites
    results = await process_all_sites(base_path, geocode_cache, chroma_cache, dry_run=args.dry_run)

    # Save updated cache
    if not args.dry_run:
        save_geocode_cache(geocode_cache, cache_file)
        print(f"\nSaved geocode cache ({len(geocode_cache)} total entries)")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Files with addresses: {results['sites_processed']}")
    print(f"Files updated: {results['sites_updated']}")
    print(f"Total addresses found: {results['total_addresses']}")
    print(f"Addresses geocoded: {results['total_geocoded']}")
    print(f"New Nominatim lookups: {results['new_geocodes']}")

    if results['errors']:
        print(f"\nErrors ({len(results['errors'])}):")
        for error in results['errors'][:10]:
            print(f"  - {error}")
        if len(results['errors']) > 10:
            print(f"  ... and {len(results['errors']) - 10} more")

    print("\n" + "=" * 70)
    print("Complete!")
    print("=" * 70)


if __name__ == '__main__':
    asyncio.run(main())
