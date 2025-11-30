#!/usr/bin/env python3
"""
Fix known bad geocodes in NPS site ambers-data.md files.

These corrections are based on official NPS coordinates and verified locations.
"""
import re
from pathlib import Path

# Corrections: site_folder -> (correct_lat, correct_lon, correct_state)
GEOCODE_CORRECTIONS = {
    # Virginia sites with wrong coords
    'Fort Monroe NM': (37.0048, -76.3083, 'Virginia'),  # Fort Monroe, VA
    'Colonial NHP': (37.2296, -76.5096, 'Virginia'),  # Yorktown, VA
    'George Washington Birthplace NM': (38.1857, -76.9313, 'Virginia'),  # Colonial Beach, VA
    'Shenandoah NP': (38.2928, -78.6796, 'Virginia'),  # Front Royal, VA
    'Richmond NBP': (37.4218, -77.3541, 'Virginia'),  # Richmond, VA
    'Petersburg NB': (37.2274, -77.3578, 'Virginia'),  # Petersburg, VA
    'Assateague Island NS': (37.9188, -75.3521, 'Virginia'),  # Chincoteague, VA
    'Historic Jamestowne': (37.2097, -76.7781, 'Virginia'),  # Jamestown, VA
    'Manassas NBP': (38.8126, -77.5216, 'Virginia'),  # Manassas, VA
    'Great Falls Park': (38.9959, -77.2548, 'Virginia'),  # McLean, VA
    'Cedar Creek and Belle Grove NHP': (39.0296, -78.3255, 'Virginia'),  # Middletown, VA
    'George Washington MEM PKWY': (38.9614, -77.1464, 'Virginia'),  # McLean, VA
    'Prince William Forest Park': (38.5815, -77.3842, 'Virginia'),  # Triangle, VA

    # West Virginia sites
    'Bluestone NSR': (37.5619, -80.8970, 'West Virginia'),  # Hinton, WV
    'Gauley River NRA': (38.2107, -80.9012, 'West Virginia'),  # Summersville, WV

    # Wyoming sites
    'Yellowstone NP': (44.4280, -110.5885, 'Wyoming'),  # Mammoth, WY
    'Grand Teton NP': (43.7904, -110.6818, 'Wyoming'),  # Moose, WY
    'John D Rockefeller, Jr Memorial Parkway': (43.8549, -110.6618, 'Wyoming'),  # Moose, WY
    'Fossil Butte NM': (41.8575, -110.7661, 'Wyoming'),  # Kemmerer, WY
    'Fort Laramie NHS': (42.2127, -104.5455, 'Wyoming'),  # Fort Laramie, WY
    'Mormon Pioneer NHT': (42.8666, -106.3125, 'Wyoming'),  # Casper, WY

    # Alabama sites
    'Tuskegee Airmen NHS': (32.4579, -85.6850, 'Alabama'),  # Tuskegee, AL
    'Tuskegee Institute NHS': (32.4289, -85.7084, 'Alabama'),  # Tuskegee, AL
}


def fix_ambers_data_file(site_folder: str, lat: float, lon: float, state: str):
    """Fix the geocode in an ambers-data.md file."""
    base_path = Path('2-Enhanced Data/NPS')
    file_path = base_path / site_folder / 'ambers-data.md'

    if not file_path.exists():
        print(f"  WARNING: File not found: {file_path}")
        return False

    content = file_path.read_text()
    original = content

    # Pattern to match address line with geocode: city, ZIPCODE (lat, lon)
    # or city, State ZIPCODE (lat, lon)
    pattern = r'(\*\*Address:\*\*[^(]+)\([-\d.]+,\s*[-\d.]+\)'

    def replace_coords(match):
        address_part = match.group(1)
        # Clean up the address - replace zip-only state with proper state
        # Look for patterns like ", 23651 " and replace with ", Virginia 23651 "
        zip_pattern = r',\s+(\d{5})\s*$'
        zip_match = re.search(zip_pattern, address_part.strip())
        if zip_match:
            zipcode = zip_match.group(1)
            address_part = re.sub(zip_pattern, f', {state} {zipcode} ', address_part.strip())
        return f'{address_part}({lat}, {lon})'

    new_content = re.sub(pattern, replace_coords, content)

    if new_content != original:
        file_path.write_text(new_content)
        print(f"  FIXED: {site_folder}")
        print(f"    New coords: ({lat}, {lon})")
        print(f"    State: {state}")
        return True
    else:
        print(f"  NO CHANGE: {site_folder} (pattern not matched)")
        return False


def main():
    print("=" * 70)
    print("FIXING BAD GEOCODES IN AMBERS-DATA.MD FILES")
    print("=" * 70)

    fixed = 0
    failed = 0

    for site_folder, (lat, lon, state) in GEOCODE_CORRECTIONS.items():
        print(f"\nProcessing: {site_folder}")
        if fix_ambers_data_file(site_folder, lat, lon, state):
            fixed += 1
        else:
            failed += 1

    print("\n" + "=" * 70)
    print(f"SUMMARY: Fixed {fixed}, Failed {failed}")
    print("=" * 70)


if __name__ == "__main__":
    main()
