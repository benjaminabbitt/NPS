#!/usr/bin/env python3
"""Find NPS sites within a specified distance of St. Louis, MO."""

import csv
import math
from pathlib import Path
from typing import List, Tuple

# St. Louis, MO coordinates
STL_LAT = 38.627
STL_LON = -90.199
MAX_DISTANCE_MILES = 500


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points on earth in miles."""
    R = 3959  # Earth's radius in miles

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    return R * c


def parse_csv() -> List[dict]:
    """Parse the NPS CSV file and return list of sites within range."""
    csv_path = Path("1-Raw Input Data/NPS/Untitled spreadsheet - US Parks.csv")
    sites_within_range = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            park_name = row.get('National Park', '').strip()
            if not park_name:
                continue

            # For now, we'll use approximate state-based filtering
            # States within ~500 miles of St. Louis:
            # Illinois, Missouri, Kentucky, Tennessee, Indiana, Arkansas, Iowa, Wisconsin (partial)
            # The state is actually in the first column labeled 'State' with a colon
            state_with_colon = row.get('State', '').strip()

            if state_with_colon in ['ILLINOIS:', 'MISSOURI:', 'KENTUCKY:', 'TENNESSEE:', 'INDIANA:',
                        'ARKANSAS:', 'IOWA:', 'WISCONSIN:', 'KANSAS:', 'NEBRASKA:', 'OKLAHOMA:',
                        'MISSISSIPPI:', 'ALABAMA:', 'OHIO:', 'MICHIGAN:', 'LOUISIANA:']:
                # Get the actual state from the 8th column
                actual_state = row.get('State.1', row.get('State', '')).strip() if 'State.1' in row else ''

                sites_within_range.append({
                    'name': park_name,
                    'address': row.get('Address', '').strip(),
                    'city': row.get('City', '').strip(),
                    'state': state_with_colon.replace(':', ''),
                    'actual_state': actual_state,
                    'zip': row.get('Zip', '').strip(),
                    'visitor_center': row.get('Visitor Center Location', '').strip(),
                    'vc_address': row.get('Visitor Center Address', '').strip(),
                    'vc_city': row.get('Visitor Center City', '').strip(),
                })

    return sites_within_range


if __name__ == '__main__':
    sites = parse_csv()

    print(f"Found {len(sites)} NPS sites potentially within 500 miles of St. Louis, MO:\n")

    # Group by state for easier reading
    by_state = {}
    for site in sites:
        state = site['state']
        if state not in by_state:
            by_state[state] = []
        by_state[state].append(site)

    for state in sorted(by_state.keys()):
        print(f"\n{state}:")
        for site in by_state[state]:
            print(f"  - {site['name']}")

    print(f"\n\nTotal: {len(sites)} sites")
