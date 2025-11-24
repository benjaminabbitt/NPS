#!/usr/bin/env python3
"""
Update Cancellation Stamps with geocoded coordinates
- Extracts addresses from cancellation stamp entries
- Geocodes addresses (using existing cache)
- Adds coordinates after addresses
- Marks visitor centers from Amber's Data as checked
"""
import json
import re
import asyncio
import httpx
import urllib.parse
from pathlib import Path
from typing import Dict, Optional, Tuple, List


# Geocode cache
GEOCODE_CACHE_FILE = Path("geocode_cache.json")


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


async def geocode_address(address: str, cache: Dict) -> Optional[Tuple[float, float]]:
    """Geocode an address using Nominatim (with caching)"""
    # Clean address for geocoding
    clean_addr = address.strip()

    if clean_addr in cache:
        coords = cache[clean_addr]
        if coords:
            return tuple(coords)
        return None

    try:
        async with httpx.AsyncClient() as client:
            url = f"https://nominatim.openstreetmap.org/search?{urllib.parse.urlencode({'q': clean_addr, 'format': 'json', 'limit': 1})}"
            headers = {'User-Agent': 'NPS-Data-Processor/1.0'}

            response = await client.get(url, headers=headers, timeout=10.0)
            data = response.json()

            if data:
                coords = (float(data[0]['lat']), float(data[0]['lon']))
                cache[clean_addr] = list(coords)
                save_geocode_cache(cache)
                await asyncio.sleep(1.1)  # Rate limiting
                return coords
            else:
                cache[clean_addr] = None
                save_geocode_cache(cache)

    except Exception as e:
        print(f"  ⚠ Geocoding error for {clean_addr}: {e}")
        cache[clean_addr] = None
        save_geocode_cache(cache)

    return None


def extract_ambers_visitor_center(content: str) -> Optional[str]:
    """Extract visitor center name from Amber's Data section"""
    match = re.search(r"## Amber's Data.*?\*\*Visitor Center:\*\* (.+?)(?:\n|$)", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def parse_cancellation_stamp_line(line: str) -> Optional[Dict]:
    """
    Parse a cancellation stamp line to extract:
    - checkbox state
    - name
    - address (if present)
    - existing coordinates (if present)

    Format: - [ ] Name (address) or - [ ] Name (address) (lat, lon)
    """
    # Match checkbox
    checkbox_match = re.match(r'^- \[([ x])\] (.+)', line.strip())
    if not checkbox_match:
        return None

    checked = checkbox_match.group(1) == 'x'
    rest = checkbox_match.group(2)

    # Check if coordinates already present: (address) (lat, lon)
    coords_match = re.search(r'\(([^)]+)\)\s*\(([-\d.]+),\s*([-\d.]+)\)\s*$', rest)
    if coords_match:
        # Already has coordinates
        name = rest[:coords_match.start()].strip()
        address = coords_match.group(1).strip()
        coords = (float(coords_match.group(2)), float(coords_match.group(3)))
        return {
            'checked': checked,
            'name': name,
            'address': address,
            'coords': coords,
            'has_coords': True
        }

    # No coordinates: (address)
    addr_match = re.search(r'\(([^)]+)\)\s*$', rest)
    if addr_match:
        name = rest[:addr_match.start()].strip()
        address = addr_match.group(1).strip()
        return {
            'checked': checked,
            'name': name,
            'address': address,
            'coords': None,
            'has_coords': False
        }

    # No address at all
    return {
        'checked': checked,
        'name': rest.strip(),
        'address': None,
        'coords': None,
        'has_coords': False
    }


def format_cancellation_stamp_line(stamp: Dict) -> str:
    """Format a cancellation stamp line"""
    checkbox = '[x]' if stamp['checked'] else '[ ]'

    if stamp['address']:
        if stamp['coords']:
            return f"- {checkbox} {stamp['name']} ({stamp['address']}) ({stamp['coords'][0]}, {stamp['coords'][1]})"
        else:
            return f"- {checkbox} {stamp['name']} ({stamp['address']})"
    else:
        return f"- {checkbox} {stamp['name']}"


async def update_cancellation_stamps_for_site(site_dir: Path, geocode_cache: Dict) -> bool:
    """Update cancellation stamps in a site's user-data.md"""
    user_data_file = site_dir / "user-data.md"

    if not user_data_file.exists():
        return False

    # Read content
    with open(user_data_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if there's a cancellation stamps section
    if "## Cancellation Stamps" not in content:
        return False

    # Extract Amber's visitor center name
    ambers_vc = extract_ambers_visitor_center(content)

    # Split content into sections
    parts = content.split("## Cancellation Stamps")
    if len(parts) != 2:
        return False

    before_stamps = parts[0]
    after_stamps_content = parts[1]

    # Find the end of cancellation stamps section (next ## heading or end)
    next_section_match = re.search(r'\n## ', after_stamps_content)
    if next_section_match:
        stamps_content = after_stamps_content[:next_section_match.start()]
        after_section = after_stamps_content[next_section_match.start():]
    else:
        stamps_content = after_stamps_content
        after_section = ""

    # Parse stamp lines
    lines = stamps_content.split('\n')
    updated_lines = []
    modified = False

    for line in lines:
        if not line.strip() or not line.strip().startswith('- ['):
            updated_lines.append(line)
            continue

        stamp = parse_cancellation_stamp_line(line)
        if not stamp:
            updated_lines.append(line)
            continue

        # Check if this matches Amber's visitor center
        if ambers_vc and stamp['name'].lower() in ambers_vc.lower() or (ambers_vc and ambers_vc.lower() in stamp['name'].lower()):
            if not stamp['checked']:
                stamp['checked'] = True
                modified = True
                print(f"    ✓ Marked '{stamp['name']}' as checked")

        # Geocode if has address but no coords
        if stamp['address'] and not stamp['has_coords']:
            coords = await geocode_address(stamp['address'], geocode_cache)
            if coords:
                stamp['coords'] = coords
                stamp['has_coords'] = True
                modified = True
                print(f"    📍 Added coordinates to '{stamp['name']}'")

        # Format and add
        updated_lines.append(format_cancellation_stamp_line(stamp))

    if not modified:
        return False

    # Reconstruct content
    new_content = before_stamps + "## Cancellation Stamps" + '\n'.join(updated_lines) + after_section

    # Write back
    with open(user_data_file, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return True


async def main():
    """Main processing function"""
    print("="*80)
    print("Updating Cancellation Stamps with Geocoded Coordinates")
    print("="*80)

    # Load geocode cache
    print("\nLoading geocode cache...")
    geocode_cache = load_geocode_cache()
    print(f"✓ Loaded {len(geocode_cache)} cached geocodes")

    # Find all site directories
    nps_dir = Path("2-Enhanced Data/NPS")
    site_dirs = [d for d in nps_dir.iterdir() if d.is_dir()]

    print(f"\nProcessing {len(site_dirs)} site directories...")
    print("-" * 80)

    processed = 0
    skipped = 0

    for site_dir in sorted(site_dirs):
        site_name = site_dir.name

        try:
            result = await update_cancellation_stamps_for_site(site_dir, geocode_cache)
            if result:
                print(f"\n{site_name}")
                processed += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"\n{site_name}")
            print(f"  ✗ Error: {e}")
            skipped += 1

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"✓ Updated: {processed}")
    print(f"⚠ Skipped: {skipped}")
    print(f"📍 Total geocodes in cache: {len(geocode_cache)}")
    print("\nGeocodes saved to: geocode_cache.json")


if __name__ == '__main__':
    asyncio.run(main())
