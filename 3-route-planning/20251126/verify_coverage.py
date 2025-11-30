#!/usr/bin/env python3
"""
Verify that all lower-48 NPS sites are covered by either:
1. St. Louis 2-day trips
2. St. Louis 3-day trips
3. Airport-based trips
"""
import sys
sys.path.insert(0, '/workspace/src/routing')

import yaml
from pathlib import Path
from nps_data_loader import NPSDataLoader

# Non-lower-48 states to exclude
EXCLUDED_STATES = {'Alaska', 'Hawaii', 'AK', 'HI', 'Puerto Rico', 'PR',
                   'Virgin Islands', 'VI', 'Guam', 'GU', 'American Samoa', 'AS'}


def load_sites_from_yaml(yaml_path):
    """Extract site names from a trip YAML file."""
    sites = set()
    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    if 'trips' in data:
        for trip in data['trips']:
            for site in trip.get('sites', []):
                sites.add(site['name'])
    elif 'trips_by_airport' in data:
        for airport_data in data['trips_by_airport'].values():
            for trip in airport_data.get('trips', []):
                for site in trip.get('sites', []):
                    sites.add(site['name'])

    return sites


def main():
    print("=" * 70)
    print("COVERAGE VERIFICATION")
    print("=" * 70)

    output_dir = Path("/workspace/3-route-planning/20251126")

    # Load all sites from database
    loader = NPSDataLoader()
    all_sites = loader.load_all_sites()

    # Get lower-48 sites only
    lower_48_sites = set()
    excluded_sites = set()

    for name, site in all_sites.items():
        if site.state in EXCLUDED_STATES:
            excluded_sites.add(name)
        else:
            lower_48_sites.add(name)

    print(f"\nTotal sites in database: {len(all_sites)}")
    print(f"Lower-48 sites: {len(lower_48_sites)}")
    print(f"Excluded (AK/HI/territories): {len(excluded_sites)}")

    # Load covered sites from each trip file
    stl_2day_sites = load_sites_from_yaml(output_dir / "2day_optimized_trips.yaml")
    stl_3day_sites = load_sites_from_yaml(output_dir / "3day_optimized_trips.yaml")
    airport_sites = load_sites_from_yaml(output_dir / "airport_trips.yaml")

    print(f"\nSt. Louis 2-day trips: {len(stl_2day_sites)} sites")
    print(f"St. Louis 3-day trips: {len(stl_3day_sites)} sites")
    print(f"Airport trips: {len(airport_sites)} sites")

    # Combine all covered sites
    all_covered = stl_2day_sites | stl_3day_sites | airport_sites
    print(f"\nTotal unique sites covered: {len(all_covered)}")

    # Check for overlap between STL and airport trips
    stl_all = stl_2day_sites | stl_3day_sites
    overlap = stl_all & airport_sites
    if overlap:
        print(f"\nWARNING: {len(overlap)} sites appear in BOTH STL and airport trips:")
        for site in sorted(overlap):
            print(f"  - {site}")

    # Find uncovered lower-48 sites
    uncovered = lower_48_sites - all_covered

    print("\n" + "=" * 70)
    if uncovered:
        print(f"UNCOVERED LOWER-48 SITES: {len(uncovered)}")
        print("=" * 70)
        for site in sorted(uncovered):
            site_data = all_sites[site]
            print(f"  - {site} ({site_data.city}, {site_data.state})")
    else:
        print("ALL LOWER-48 SITES ARE COVERED!")
        print("=" * 70)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Lower-48 sites in database: {len(lower_48_sites)}")
    print(f"Sites covered by trips: {len(all_covered)}")
    print(f"Uncovered sites: {len(uncovered)}")
    print(f"Coverage: {len(all_covered - excluded_sites)}/{len(lower_48_sites)} = {100 * len(all_covered & lower_48_sites) / len(lower_48_sites):.1f}%")

    # Breakdown
    print("\nBreakdown:")
    print(f"  St. Louis 2-day: {len(stl_2day_sites)} sites")
    print(f"  St. Louis 3-day: {len(stl_3day_sites)} sites")
    print(f"  Airport trips: {len(airport_sites)} sites")

    return uncovered


if __name__ == "__main__":
    main()
