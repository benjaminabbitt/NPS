#!/usr/bin/env python3
"""
Add geocode coordinates to all addresses in completed NPS site markdown files
"""

import json
import re
import asyncio
import httpx
import urllib.parse
from pathlib import Path
import chromadb


# List of 20 completed sites
SITES = [
    "Abraham Lincoln Birthplace NHP",
    "Acadia NP",
    "Alcatraz Island",
    "Adams NHP",
    "African Burial Ground NM",
    "Agate Fossil Beds NM",
    "Alibates Flint Quarries NM",
    "African American Civil War MEM",
    "Alagnak WR",
    "Aleutian World War II NHA",
    "Apostle Islands NL",
    "Andersonville NHS",
    "Antietam NB",
    "Allegheny Portage Railroad NHS",
    "Andrew Johnson NHS",
    "Aniakchak NM _ PRES",
    "Amache NHS",
    "American Veterans Disabled for Life Memorial",
    "Anacostia Park",
    "Amistad NRA"
]


def load_geocode_cache():
    """Load existing geocode cache"""
    cache_file = Path('geocode_cache.json')
    if cache_file.exists():
        with open(cache_file, 'r') as f:
            return json.load(f)
    return {}


def save_geocode_cache(cache):
    """Save geocode cache"""
    with open('geocode_cache.json', 'w') as f:
        json.dump(cache, f, indent=2)


async def geocode_address(address: str, cache: dict) -> tuple:
    """Geocode an address, using cache if available"""
    # Check cache first
    if address in cache:
        coords = cache[address]
        if coords and isinstance(coords, (list, tuple)) and len(coords) == 2:
            return tuple(coords)

    # Geocode using Nominatim
    try:
        async with httpx.AsyncClient() as client:
            url = f"https://nominatim.openstreetmap.org/search?{urllib.parse.urlencode({'q': address, 'format': 'json', 'limit': 1})}"
            headers = {'User-Agent': 'NPS-Geocoder/1.0'}

            response = await client.get(url, headers=headers, timeout=10.0)
            data = response.json()

            if data:
                coords = (float(data[0]['lat']), float(data[0]['lon']))
                cache[address] = coords
                await asyncio.sleep(1.1)  # Rate limiting
                return coords
    except Exception as e:
        print(f"  Error geocoding '{address}': {e}")

    return None


def extract_address_from_parentheses(text: str) -> str:
    """Extract just the address part (before first semicolon)"""
    # Remove leading parenthesis
    text = text.lstrip('(')
    # Get everything before first semicolon
    parts = text.split(';')
    return parts[0].strip()


async def process_site(site_name: str, geocode_cache: dict) -> bool:
    """Process a single site's markdown file to add geocodes"""
    # Find the markdown file
    base_path = Path('2-Enhanced Data/NPS')
    site_path = base_path / site_name
    md_file = site_path / f"{site_name}.md"

    if not md_file.exists():
        print(f"✗ {site_name}: File not found at {md_file}")
        return False

    print(f"\n{'='*70}")
    print(f"Processing: {site_name}")
    print(f"{'='*70}")

    # Read the file
    content = md_file.read_text()
    original_content = content

    # Pattern to find addresses in format: (address; hours; phone)
    # This matches content in parentheses that contains semicolons
    pattern = r'\(([^()]+;[^()]+)\)'

    matches = list(re.finditer(pattern, content))
    print(f"Found {len(matches)} potential address entries")

    modified = False
    addresses_geocoded = 0

    for match in reversed(matches):  # Process in reverse to maintain positions
        full_match = match.group(0)  # e.g., "(123 Main St, City, ST 12345; 9AM-5PM; 555-1234)"
        inner_content = match.group(1)

        # Extract the address (before first semicolon)
        address = extract_address_from_parentheses(full_match)

        # Skip if it's not a real address (too short, no state codes, etc.)
        if len(address) < 10:
            continue

        # Skip if it already has coordinates (contains lat/lon pattern)
        if re.search(r'\(\s*-?\d+\.\d+\s*,\s*-?\d+\.\d+\s*\)', full_match):
            print(f"  ✓ Already has coords: {address[:50]}...")
            continue

        # Geocode the address
        print(f"  → Geocoding: {address}")
        coords = await geocode_address(address, geocode_cache)

        if coords:
            # Format: (address (lat, lon); hours; phone)
            # Insert coordinates after address but before semicolon
            parts = inner_content.split(';', 1)
            if len(parts) == 2:
                new_content = f"({parts[0].strip()} ({coords[0]}, {coords[1]}); {parts[1].strip()})"
                content = content[:match.start()] + new_content + content[match.end():]
                modified = True
                addresses_geocoded += 1
                print(f"    ✓ Added coordinates: {coords}")

    if modified:
        # Save the updated file
        md_file.write_text(content)
        print(f"\n✓ Updated {site_name}: Added {addresses_geocoded} geocode(s)")
        return True
    else:
        print(f"\n○ No changes needed for {site_name}")
        return False


async def update_chroma_collection():
    """Update Chroma database with modified files"""
    print(f"\n{'='*70}")
    print("Updating Chroma database...")
    print(f"{'='*70}")

    # This would need to re-sync the files to Chroma
    # For now, just a placeholder
    print("Note: Chroma sync should be run separately")


async def main():
    """Main execution"""
    print("="*70)
    print("Adding Geocodes to NPS Site Addresses")
    print("="*70)

    # Load geocode cache
    geocode_cache = load_geocode_cache()
    print(f"\nLoaded {len(geocode_cache)} cached geocodes")

    # Process each site
    updated_sites = []
    for site in SITES:
        success = await process_site(site, geocode_cache)
        if success:
            updated_sites.append(site)

    # Save updated cache
    save_geocode_cache(geocode_cache)
    print(f"\n{'='*70}")
    print(f"Saved geocode cache with {len(geocode_cache)} entries")

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Sites processed: {len(SITES)}")
    print(f"Sites updated: {len(updated_sites)}")
    print(f"\nUpdated sites:")
    for site in updated_sites:
        print(f"  ✓ {site}")

    print(f"\n{'='*70}")
    print("Complete!")
    print(f"{'='*70}")


if __name__ == '__main__':
    asyncio.run(main())
