#!/usr/bin/env python3
"""
Add Amber's Data from CSV spreadsheet to user-data.md files
- Extracts visitor center address and hours from CSV
- Geocodes addresses
- Adds "Amber's Data" section to user-data.md
- Ensures visitor center is listed in cancellation stamps
"""
import csv
import json
import time
import asyncio
import httpx
import urllib.parse
from pathlib import Path
from typing import Dict, Optional, Tuple


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
    if address in cache:
        coords = cache[address]
        if coords:
            return tuple(coords)
        return None

    try:
        async with httpx.AsyncClient() as client:
            url = f"https://nominatim.openstreetmap.org/search?{urllib.parse.urlencode({'q': address, 'format': 'json', 'limit': 1})}"
            headers = {'User-Agent': 'NPS-Data-Processor/1.0'}

            response = await client.get(url, headers=headers, timeout=10.0)
            data = response.json()

            if data:
                coords = (float(data[0]['lat']), float(data[0]['lon']))
                cache[address] = list(coords)
                save_geocode_cache(cache)
                await asyncio.sleep(1.1)  # Rate limiting
                return coords
            else:
                cache[address] = None
                save_geocode_cache(cache)

    except Exception as e:
        print(f"  ⚠ Geocoding error for {address}: {e}")
        cache[address] = None
        save_geocode_cache(cache)

    return None


def read_csv_data() -> Dict[str, Dict]:
    """Read CSV and extract site data"""
    csv_file = Path("1-Raw Input Data/NPS/Untitled spreadsheet - US Parks.csv")

    if not csv_file.exists():
        print(f"Error: CSV file not found at {csv_file}")
        return {}

    sites_data = {}

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            site_name = row.get('National Park', '').strip()
            if not site_name:
                continue

            # Visitor Center info
            vc_name = row.get('Visitor Center Location', '').strip()
            vc_address = row.get('Visitor Center Address', '').strip()
            vc_city = row.get('Visitor Center City', '').strip()
            vc_state = row.get('Visitor Center State', '').strip()
            vc_zip = row.get('Visitor Center Zip', '').strip()

            # Build full address
            if vc_address and vc_city and vc_state:
                full_address = f"{vc_address}, {vc_city}, {vc_state} {vc_zip}".strip()
            else:
                full_address = None

            # Hours (from Visitor Center columns - Sunday through Saturday)
            hours = {
                'Sunday': row.get('Sunday.1', '').strip(),
                'Monday': row.get('Monday.1', '').strip(),
                'Tuesday': row.get('Tuesday.1', '').strip(),
                'Wednesday': row.get('Wednesday.1', '').strip(),
                'Thursday': row.get('Thursday.1', '').strip(),
                'Friday': row.get('Friday.1', '').strip(),
                'Saturday': row.get('Saturday.1', '').strip()
            }

            sites_data[site_name] = {
                'visitor_center_name': vc_name,
                'visitor_center_address': full_address,
                'hours': hours
            }

    return sites_data


def format_hours(hours: Dict[str, str]) -> str:
    """Format hours dictionary into readable string"""
    if not any(hours.values()):
        return "Hours not available"

    # Check if all days have same hours
    unique_hours = list(set(h for h in hours.values() if h))

    if len(unique_hours) == 1:
        return f"Daily {unique_hours[0]}"

    # Group consecutive days with same hours
    days_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    formatted = []

    current_hours = None
    current_days = []

    for day in days_order:
        day_hours = hours.get(day, '')

        if day_hours == current_hours:
            current_days.append(day)
        else:
            if current_hours and current_days:
                day_range = format_day_range(current_days)
                formatted.append(f"{day_range}: {current_hours}")
            current_hours = day_hours
            current_days = [day]

    # Add final group
    if current_hours and current_days:
        day_range = format_day_range(current_days)
        formatted.append(f"{day_range}: {current_hours}")

    return "; ".join(formatted)


def format_day_range(days: list) -> str:
    """Format list of days into range"""
    if len(days) == 1:
        return days[0]
    elif len(days) == 7:
        return "Daily"
    else:
        return f"{days[0]}-{days[-1]}"


async def add_ambers_data_to_site(site_name: str, site_data: Dict, geocode_cache: Dict) -> bool:
    """Add Amber's Data section to a site's user-data.md file"""
    # Find the site directory
    site_dir = Path(f"2-Enhanced Data/NPS/{site_name}")

    if not site_dir.exists():
        print(f"  ⚠ Directory not found: {site_dir}")
        return False

    user_data_file = site_dir / "user-data.md"

    if not user_data_file.exists():
        print(f"  ⚠ user-data.md not found in {site_dir}")
        return False

    # Read existing content
    with open(user_data_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if Amber's Data already exists
    if "## Amber's Data" in content:
        print(f"  ℹ Amber's Data already exists in {site_name}")
        return True

    # Geocode address if we have one
    vc_address = site_data['visitor_center_address']
    coordinates = None

    if vc_address:
        coordinates = await geocode_address(vc_address, geocode_cache)

    # Build Amber's Data section
    ambers_data = "\n## Amber's Data (from spreadsheet)\n\n"

    if site_data['visitor_center_name']:
        ambers_data += f"**Visitor Center:** {site_data['visitor_center_name']}\n\n"

    if vc_address:
        if coordinates:
            ambers_data += f"**Address:** {vc_address} ({coordinates[0]}, {coordinates[1]})\n\n"
        else:
            ambers_data += f"**Address:** {vc_address}\n\n"

    hours_str = format_hours(site_data['hours'])
    ambers_data += f"**Hours:** {hours_str}\n\n"

    # Insert before "Review / Personal Notes" section
    if "## Review / Personal Notes" in content:
        parts = content.split("## Review / Personal Notes")
        new_content = parts[0] + ambers_data + "## Review / Personal Notes" + parts[1]
    else:
        # Append at end
        new_content = content + "\n" + ambers_data

    # Check if visitor center should be in cancellation stamps
    if site_data['visitor_center_name'] and "## Cancellation Stamps" in content:
        # Check if it's already there
        if site_data['visitor_center_name'] not in content:
            print(f"  ℹ Note: Visitor center '{site_data['visitor_center_name']}' should be added to Cancellation Stamps")

    # Write updated content
    with open(user_data_file, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"  ✓ Added Amber's Data to {site_name}")
    return True


async def main():
    """Main processing function"""
    print("="*80)
    print("Adding Amber's Data from CSV Spreadsheet")
    print("="*80)

    # Load geocode cache
    print("\nLoading geocode cache...")
    geocode_cache = load_geocode_cache()
    print(f"✓ Loaded {len(geocode_cache)} cached geocodes")

    # Read CSV data
    print("\nReading CSV spreadsheet...")
    sites_data = read_csv_data()
    print(f"✓ Found {len(sites_data)} sites in CSV")

    # Process each site
    print("\nProcessing sites...")
    print("-" * 80)

    processed = 0
    skipped = 0

    for site_name, site_data in sites_data.items():
        print(f"\n{site_name}")

        if not site_data['visitor_center_address']:
            print(f"  ⚠ No visitor center address in CSV")
            skipped += 1
            continue

        success = await add_ambers_data_to_site(site_name, site_data, geocode_cache)

        if success:
            processed += 1
        else:
            skipped += 1

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"✓ Processed: {processed}")
    print(f"⚠ Skipped: {skipped}")
    print(f"📍 Total geocodes in cache: {len(geocode_cache)}")
    print("\nGeocodes saved to: geocode_cache.json")


if __name__ == '__main__':
    asyncio.run(main())
