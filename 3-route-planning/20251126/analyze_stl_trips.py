#!/usr/bin/env python3
"""
Analyze NPS sites reachable from St. Louis in 2-day and 3-day trips.
"""
import sys
sys.path.insert(0, '/workspace/src/routing')

import math
from pathlib import Path
from nps_data_loader import NPSDataLoader

# St. Louis (Kirkwood) home base
HOME_LAT = 38.5831
HOME_LON = -90.4068

def haversine(lat1, lon1, lat2, lon2):
    """Distance in miles"""
    R = 3959
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def main():
    print("=" * 70)
    print("NPS SITES FROM ST. LOUIS - DISTANCE ANALYSIS")
    print("=" * 70)
    print(f"Home base: Kirkwood, MO ({HOME_LAT}, {HOME_LON})")
    print()

    # Load all sites
    loader = NPSDataLoader()
    all_sites = loader.load_all_sites()

    # Calculate distances
    sites_with_dist = []
    for name, site in all_sites.items():
        dist = haversine(HOME_LAT, HOME_LON, site.lat, site.lon)
        sites_with_dist.append((name, site, dist))

    # Sort by distance
    sites_with_dist.sort(key=lambda x: x[2])

    # Distance thresholds based on trip duration
    # 2 days: 2 × 10 × 55 × 0.4 = 440 miles
    # 3 days: 3 × 10 × 55 × 0.4 = 660 miles
    TWO_DAY_RADIUS = 440
    THREE_DAY_RADIUS = 660

    # Categorize sites
    two_day_sites = [(n, s, d) for n, s, d in sites_with_dist if d <= TWO_DAY_RADIUS]
    three_day_only = [(n, s, d) for n, s, d in sites_with_dist if TWO_DAY_RADIUS < d <= THREE_DAY_RADIUS]
    beyond = [(n, s, d) for n, s, d in sites_with_dist if d > THREE_DAY_RADIUS]

    print(f"Distance thresholds:")
    print(f"  2-day trips: ≤{TWO_DAY_RADIUS} miles")
    print(f"  3-day trips: ≤{THREE_DAY_RADIUS} miles")
    print()

    print(f"=" * 70)
    print(f"2-DAY TRIP SITES ({len(two_day_sites)} sites within {TWO_DAY_RADIUS} miles)")
    print(f"=" * 70)
    for name, site, dist in two_day_sites:
        print(f"  {dist:6.1f} mi - {name} ({site.city}, {site.state})")

    print()
    print(f"=" * 70)
    print(f"3-DAY TRIP SITES ({len(three_day_only)} additional sites, {TWO_DAY_RADIUS}-{THREE_DAY_RADIUS} miles)")
    print(f"=" * 70)
    for name, site, dist in three_day_only:
        print(f"  {dist:6.1f} mi - {name} ({site.city}, {site.state})")

    print()
    print(f"=" * 70)
    print(f"SUMMARY")
    print(f"=" * 70)
    print(f"  2-day reachable: {len(two_day_sites)} sites")
    print(f"  3-day additional: {len(three_day_only)} sites")
    print(f"  Total 3-day reachable: {len(two_day_sites) + len(three_day_only)} sites")
    print(f"  Beyond 3 days: {len(beyond)} sites")

    # Save to files for checklist creation
    output_dir = Path("/workspace/3-route-planning/20251126")
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "2day_sites.txt", "w") as f:
        for name, site, dist in two_day_sites:
            f.write(f"{dist:.1f}|{name}|{site.city}|{site.state}|{site.lat}|{site.lon}\n")

    with open(output_dir / "3day_additional_sites.txt", "w") as f:
        for name, site, dist in three_day_only:
            f.write(f"{dist:.1f}|{name}|{site.city}|{site.state}|{site.lat}|{site.lon}\n")

    print(f"\nSaved site lists to {output_dir}/")

    return two_day_sites, three_day_only


if __name__ == "__main__":
    main()
