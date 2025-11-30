#!/usr/bin/env python3
"""
Add geocode coordinates to addresses in NPS site markdown files.
Version 2: Simpler pattern matching that handles nested parentheses.
"""

import json
import re
import asyncio
import httpx
import urllib.parse
from pathlib import Path
from typing import Optional, Tuple, Dict

# State abbreviation to full name mapping
ABBREV_TO_STATE = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
    'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
    'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
    'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
    'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
    'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
    'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
    'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
    'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
    'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia'
}


def normalize_address(addr: str) -> str:
    """Convert ST abbreviation to full state name for cache lookup"""
    for abbrev, state in ABBREV_TO_STATE.items():
        # Match ', ST 12345' pattern
        pattern = rf',\s*{abbrev}\s+(\d{{5}})'
        addr = re.sub(pattern, f', {state}, \\1', addr)
    return addr


def lookup_geocode(address: str, cache: Dict, chroma_cache: Dict) -> Optional[Tuple[float, float]]:
    """Look up geocode from caches"""
    for lookup_addr in [address, normalize_address(address)]:
        for c in [cache, chroma_cache]:
            if lookup_addr in c:
                coords = c[lookup_addr]
                if coords and len(coords) == 2:
                    return tuple(coords)
    return None


async def geocode_via_nominatim(
    address: str,
    cache: Dict,
    client: httpx.AsyncClient,
    stats: dict
) -> Optional[Tuple[float, float]]:
    """Geocode address via Nominatim API"""
    try:
        url = f"https://nominatim.openstreetmap.org/search?{urllib.parse.urlencode({'q': address, 'format': 'json', 'limit': 1})}"
        headers = {'User-Agent': 'NPS-Geocoder/1.0'}

        response = await client.get(url, headers=headers, timeout=10.0)
        data = response.json()

        if data:
            coords = (float(data[0]['lat']), float(data[0]['lon']))
            cache[address] = list(coords)
            stats['nominatim_calls'] += 1
            await asyncio.sleep(1.1)  # Rate limiting
            return coords
    except Exception as e:
        print(f"    Error: {e}")

    stats['geocode_failures'] += 1
    return None


async def process_file(
    md_file: Path,
    cache: Dict,
    chroma_cache: Dict,
    client: httpx.AsyncClient,
    stats: dict,
    dry_run: bool = False
) -> int:
    """
    Process a single markdown file.
    Returns number of geocodes added.
    """
    content = md_file.read_text(encoding='utf-8')
    original_content = content

    # Pattern: Match address ending with ZIP code, NOT followed by geocode
    # Captures: (Street Address, City, ST 12345) but only if no (lat, lon) follows
    # This regex finds: number + street + city, ST ZIP
    # where ZIP is NOT followed by space + (number
    address_pattern = r'(\d+\s+[\w\s.]+(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Blvd|Boulevard|Highway|Hwy|Way|Parkway|Pkwy|Lane|Ln)[,.\s]+[\w\s]+,\s*[A-Z]{2}\s+\d{5})(?!\s*\([-\d])'

    matches = list(re.finditer(address_pattern, content, re.IGNORECASE))
    geocodes_added = 0

    for match in reversed(matches):  # Process in reverse to maintain positions
        address = match.group(1).strip()

        # Skip if this address segment already has a geocode nearby
        # Check the next 20 chars after the match
        end_pos = match.end()
        next_chars = content[end_pos:end_pos+20]
        if re.match(r'\s*\(\s*-?\d+\.\d+', next_chars):
            continue

        # Try to get geocode
        coords = lookup_geocode(address, cache, chroma_cache)

        if not coords and stats['nominatim_calls'] < 200:  # Limit API calls
            coords = await geocode_via_nominatim(address, cache, client, stats)

        if coords:
            # Insert geocode after the address
            geocode_str = f" ({coords[0]}, {coords[1]})"
            content = content[:match.end()] + geocode_str + content[match.end():]
            geocodes_added += 1
            print(f"    + {address[:40]}... → ({coords[0]:.4f}, {coords[1]:.4f})")

    if geocodes_added > 0 and not dry_run:
        md_file.write_text(content, encoding='utf-8')

    return geocodes_added


async def main():
    import argparse

    parser = argparse.ArgumentParser(description='Add geocodes to NPS site files')
    parser.add_argument('--dry-run', action='store_true', help='Show changes without saving')
    parser.add_argument('--limit', type=int, default=0, help='Limit files to process')
    args = parser.parse_args()

    print("=" * 70)
    print("NPS Site Geocoding v2")
    print("=" * 70)

    base_path = Path('2-Enhanced Data/NPS')
    cache_file = Path('geocode_cache.json')
    chroma_cache_file = Path('chroma_geocodes_cache.json')

    # Load caches
    cache = json.load(open(cache_file)) if cache_file.exists() else {}
    chroma_cache = json.load(open(chroma_cache_file)) if chroma_cache_file.exists() else {}

    print(f"\nLoaded {len(cache)} file cache entries")
    print(f"Loaded {len(chroma_cache)} Chroma cache entries")

    if args.dry_run:
        print("\n*** DRY RUN MODE ***\n")

    stats = {
        'files_processed': 0,
        'files_updated': 0,
        'geocodes_added': 0,
        'nominatim_calls': 0,
        'geocode_failures': 0
    }

    async with httpx.AsyncClient() as client:
        site_dirs = sorted([d for d in base_path.iterdir() if d.is_dir()])

        if args.limit:
            site_dirs = site_dirs[:args.limit]

        for site_dir in site_dirs:
            for md_file in site_dir.glob('*.md'):
                if md_file.name in ('ambers-data.md', 'CLAUDE.md'):
                    continue

                stats['files_processed'] += 1

                added = await process_file(
                    md_file, cache, chroma_cache, client, stats, args.dry_run
                )

                if added > 0:
                    stats['files_updated'] += 1
                    stats['geocodes_added'] += added
                    print(f"  {site_dir.name}/{md_file.name}: +{added} geocodes")

    # Save updated cache
    if not args.dry_run:
        with open(cache_file, 'w') as f:
            json.dump(cache, f, indent=2)
        print(f"\nSaved cache ({len(cache)} entries)")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Files processed: {stats['files_processed']}")
    print(f"Files updated: {stats['files_updated']}")
    print(f"Geocodes added: {stats['geocodes_added']}")
    print(f"Nominatim API calls: {stats['nominatim_calls']}")
    print(f"Geocode failures: {stats['geocode_failures']}")


if __name__ == '__main__':
    asyncio.run(main())
