#!/usr/bin/env python3
"""
CONSOLIDATED airport-based trips for NPS sites NOT covered by St. Louis trips.

Merges sparse regional trips for efficiency:
- Utah + Colorado → Rocky Mountain & Canyon Country (LAS→DEN)
- Yellowstone + Wyoming/Dakotas → Greater Yellowstone & Plains (BIL→DEN)
- Virginia + DC/Maryland → Capital Region Grand Tour (DCA loop)

Reduces from 17 trips to 12 trips.
"""
import sys
sys.path.insert(0, '/workspace/src/routing')

import math
import yaml
from pathlib import Path
from nps_data_loader import NPSDataLoader

# Sites already covered by St. Louis trips
STL_COVERED_SITES = {
    # 2-day trips (27 sites)
    'Springfield 1908 Race Riot National Monument',
    'George Rogers Clark NHP',
    'Abraham Lincoln Birthplace NHP',
    'William Howard Taft NHS',
    'Dayton Aviation Heritage NHP',
    'Pullman NHP',
    'Herbert Hoover NHS',
    'Ice Age National Scenic Trail',
    'River Raisin NBP',
    'Buffalo NR',
    'Pea Ridge NMP',
    'Fort Smith NHS',
    'Arkansas Post N MEM',
    'Little Rock Central High School NHS',
    'Fort Donelson NB',
    'Stones River NB',
    'Big South Fork NRRA',
    'Obed WSR',
    'Great Smoky Mountains NP',
    'Birmingham Civil Rights NM',
    'Freedom Riders NM',
    'Emmett Till and Mamie Till-Mobley NM',
    'Medgar and Myrlie Evers Home NM',
    'Harry S Truman NHS',
    'Fort Scott NHS',
    'Homestead NHP',
    'Gauley River NRA',
    # 3-day trips (34 sites)
    'Oklahoma City N MEM',
    'Chickasaw NRA',
    'Mississippi NRRA',
    'Pipestone NM',
    'Pictured Rocks NL',
    'Isle Royale NP',
    'Keweenaw NHP',
    'Apostle Islands NL',
    'Grand Portage NM',
    'Sleeping Bear Dunes NL',
    'Cuyahoga Valley NP',
    'First Ladies NHS',
    'Flight 93 N MEM',
    'Friendship Hill NHS',
    'Cedar Creek and Belle Grove NHP',
    'Bluestone NSR',
    'Andrew Johnson NHS',
    'Martin Luther King, Jr NHP',
    'Chattahoochee River NRA',
    'Tuskegee Airmen NHS',
    'Tuskegee Institute NHS',
    'Jimmy Carter NHP',
    'Ocmulgee NHP',
    'Cowpens NB',
    'Ninety Six NHS',
    'Guilford Courthouse NMP',
    'Carl Sandburg Home NHS',
    'New Orleans Jazz NHP',
    'Natchez NHP',
    'Cane River Creole NHP',
    'Gulf Islands NS',
    'Fort Larned NHS',
    'Amache NHS',
    'Lake Meredith NRA',
}

EXCLUDED_STATES = {'Alaska', 'Hawaii', 'AK', 'HI', 'Puerto Rico', 'PR',
                   'Virgin Islands', 'VI', 'Guam', 'GU', 'American Samoa', 'AS'}

# CONSOLIDATED Regional trip definitions (12 trips instead of 17)
REGIONAL_TRIPS = [
    {
        'name': 'Pacific Northwest',
        'fly_in': 'SEA',
        'fly_out': 'PDX',
        'days': 10,
        'description': 'Washington, Oregon, Northern Idaho loop',
        'bounds': {'min_lat': 42.0, 'max_lat': 49.0, 'min_lon': -125.0, 'max_lon': -114.0},
    },
    {
        'name': 'Northern California & Nevada',
        'fly_in': 'SFO',
        'fly_out': 'SFO',
        'days': 10,
        'description': 'Bay Area, Point Reyes, Lassen, Sierra Nevada',
        'bounds': {'min_lat': 36.0, 'max_lat': 42.0, 'min_lon': -125.0, 'max_lon': -114.0},
    },
    {
        'name': 'Southern California & Mojave',
        'fly_in': 'LAX',
        'fly_out': 'LAS',
        'days': 10,
        'description': 'LA area, Channel Islands, Joshua Tree, Mojave, Vegas',
        'bounds': {'min_lat': 32.0, 'max_lat': 37.5, 'min_lon': -121.0, 'max_lon': -114.0},
    },
    {
        'name': 'Arizona Grand Loop',
        'fly_in': 'PHX',
        'fly_out': 'PHX',
        'days': 10,
        'description': 'All Arizona NPS sites plus Grand Canyon',
        'bounds': {'min_lat': 31.0, 'max_lat': 37.5, 'min_lon': -115.0, 'max_lon': -109.0},
        'include_states': ['Arizona'],
    },
    # MERGED: Utah + Colorado → Rocky Mountain & Canyon Country
    {
        'name': 'Rocky Mountain & Canyon Country',
        'fly_in': 'LAS',
        'fly_out': 'DEN',
        'days': 14,
        'description': 'Zion, Bryce, Utah parks, then Rocky Mountain NP and Colorado sites',
        'bounds': {'min_lat': 36.5, 'max_lat': 41.5, 'min_lon': -114.5, 'max_lon': -102.0},
        'include_states': ['Utah', 'Colorado'],
    },
    {
        'name': 'Four Corners & New Mexico',
        'fly_in': 'ABQ',
        'fly_out': 'ABQ',
        'days': 12,
        'description': 'Bandelier, Carlsbad, White Sands, Mesa Verde, Chaco',
        'bounds': {'min_lat': 31.0, 'max_lat': 38.0, 'min_lon': -110.0, 'max_lon': -103.0},
        'include_states': ['New Mexico'],
    },
    {
        'name': 'Texas Big Bend & Border',
        'fly_in': 'SAT',
        'fly_out': 'ELP',
        'days': 12,
        'description': 'San Antonio to El Paso via Big Bend and border sites',
        'bounds': {'min_lat': 25.0, 'max_lat': 32.5, 'min_lon': -107.0, 'max_lon': -96.0},
        'include_states': ['Texas'],
    },
    # MERGED: Yellowstone + Wyoming/Dakotas → Greater Yellowstone & Plains
    {
        'name': 'Greater Yellowstone & Northern Plains',
        'fly_in': 'BIL',
        'fly_out': 'DEN',
        'days': 14,
        'description': 'Yellowstone, Grand Teton, then south through Wyoming to Denver',
        'bounds': {'min_lat': 40.0, 'max_lat': 46.0, 'min_lon': -114.0, 'max_lon': -100.0},
        'include_states': ['Wyoming', 'Idaho', 'Montana', 'Nebraska'],
    },
    # MERGED: Florida + Georgia/Carolinas → Southeast Atlantic Coast
    {
        'name': 'Southeast Atlantic Coast',
        'fly_in': 'MIA',
        'fly_out': 'RDU',
        'days': 14,
        'description': 'Miami to Outer Banks - Everglades, Florida forts, Georgia coast, Carolinas',
        'bounds': {'min_lat': 24.0, 'max_lat': 36.5, 'min_lon': -88.0, 'max_lon': -75.0},
        'include_states': ['Florida', 'Georgia', 'South Carolina', 'North Carolina'],
    },
    # MERGED: Virginia + DC/Maryland → Capital Region Grand Tour
    {
        'name': 'Capital Region Grand Tour',
        'fly_in': 'DCA',
        'fly_out': 'DCA',
        'days': 14,
        'description': 'DC monuments, Maryland sites, Virginia heritage and battlefields',
        'bounds': {'min_lat': 36.5, 'max_lat': 40.0, 'min_lon': -80.5, 'max_lon': -75.0},
        'include_states': ['Virginia', 'DC', 'District of Columbia', 'Maryland'],
    },
    {
        'name': 'Pennsylvania Heritage',
        'fly_in': 'PHL',
        'fly_out': 'PHL',
        'days': 8,
        'description': 'Independence Hall, Gettysburg, Valley Forge, Steamtown',
        'bounds': {'min_lat': 39.5, 'max_lat': 42.5, 'min_lon': -80.5, 'max_lon': -74.5},
        'include_states': ['Pennsylvania', 'Delaware'],
    },
    {
        'name': 'New York Mega Tour',
        'fly_in': 'EWR',
        'fly_out': 'EWR',
        'days': 12,
        'description': 'NYC to Finger Lakes, all New York and NJ sites',
        'bounds': {'min_lat': 39.0, 'max_lat': 44.5, 'min_lon': -80.0, 'max_lon': -72.0},
    },
    {
        'name': 'New England Grand Tour',
        'fly_in': 'BOS',
        'fly_out': 'BOS',
        'days': 14,
        'description': 'Boston Freedom Trail to Acadia and Maine border',
        'bounds': {'min_lat': 41.0, 'max_lat': 47.5, 'min_lon': -73.5, 'max_lon': -66.5},
        'include_states': ['Massachusetts', 'Maine', 'New Hampshire', 'Vermont',
                          'Rhode Island', 'Connecticut', 'Maine 4619', 'Maine 4553'],
    },
]

AIRPORTS = {
    'SEA': {'name': 'Seattle-Tacoma', 'lat': 47.4502, 'lon': -122.3088},
    'PDX': {'name': 'Portland', 'lat': 45.5898, 'lon': -122.5951},
    'SFO': {'name': 'San Francisco', 'lat': 37.6213, 'lon': -122.3790},
    'LAX': {'name': 'Los Angeles', 'lat': 33.9425, 'lon': -118.4081},
    'PHX': {'name': 'Phoenix', 'lat': 33.4373, 'lon': -112.0078},
    'LAS': {'name': 'Las Vegas', 'lat': 36.0840, 'lon': -115.1537},
    'ABQ': {'name': 'Albuquerque', 'lat': 35.0402, 'lon': -106.6090},
    'ELP': {'name': 'El Paso', 'lat': 31.8072, 'lon': -106.3778},
    'DEN': {'name': 'Denver', 'lat': 39.8561, 'lon': -104.6737},
    'SLC': {'name': 'Salt Lake City', 'lat': 40.7899, 'lon': -111.9791},
    'BIL': {'name': 'Billings', 'lat': 45.8077, 'lon': -108.5430},
    'SAT': {'name': 'San Antonio', 'lat': 29.5337, 'lon': -98.4698},
    'DCA': {'name': 'Washington Reagan', 'lat': 38.8512, 'lon': -77.0402},
    'PHL': {'name': 'Philadelphia', 'lat': 39.8744, 'lon': -75.2424},
    'EWR': {'name': 'Newark', 'lat': 40.6895, 'lon': -74.1745},
    'BOS': {'name': 'Boston', 'lat': 42.3656, 'lon': -71.0096},
    'JAX': {'name': 'Jacksonville', 'lat': 30.4941, 'lon': -81.6879},
    'MIA': {'name': 'Miami', 'lat': 25.7959, 'lon': -80.2870},
    'RDU': {'name': 'Raleigh-Durham', 'lat': 35.8801, 'lon': -78.7880},
}


def haversine(lat1, lon1, lat2, lon2):
    R = 3959
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def site_in_bounds(site, bounds):
    return (bounds['min_lat'] <= site['lat'] <= bounds['max_lat'] and
            bounds['min_lon'] <= site['lon'] <= bounds['max_lon'])


def site_in_states(site, states):
    return site['state'] in states


def main():
    print("=" * 70)
    print("CONSOLIDATED AIRPORT TRIPS (12 REGIONAL TRIPS)")
    print("=" * 70)

    loader = NPSDataLoader()
    all_sites = loader.load_all_sites()

    print(f"\nTotal sites in database: {len(all_sites)}")
    print(f"Sites covered by St. Louis trips: {len(STL_COVERED_SITES)}")

    remaining_sites = []
    excluded_sites = []

    for name, site in all_sites.items():
        if name in STL_COVERED_SITES:
            continue
        if site.state in EXCLUDED_STATES:
            excluded_sites.append((name, site.state))
            continue
        remaining_sites.append({
            'name': name,
            'lat': site.lat,
            'lon': site.lon,
            'city': site.city,
            'state': site.state,
        })

    print(f"Remaining lower-48 sites: {len(remaining_sites)}")

    assigned_sites = set()
    trip_plans = []

    for trip_def in REGIONAL_TRIPS:
        trip_sites = []

        for site in remaining_sites:
            if site['name'] in assigned_sites:
                continue

            if 'include_states' in trip_def:
                if not site_in_states(site, trip_def['include_states']):
                    continue

            if site_in_bounds(site, trip_def['bounds']):
                trip_sites.append(site)
                assigned_sites.add(site['name'])

        if trip_sites:
            fly_in = AIRPORTS[trip_def['fly_in']]
            fly_out = AIRPORTS[trip_def['fly_out']]

            trip_sites.sort(key=lambda s: (s['lat'], s['lon']))

            total_driving = 0
            if trip_sites:
                total_driving += haversine(fly_in['lat'], fly_in['lon'],
                                          trip_sites[0]['lat'], trip_sites[0]['lon'])
                for i in range(len(trip_sites) - 1):
                    total_driving += haversine(
                        trip_sites[i]['lat'], trip_sites[i]['lon'],
                        trip_sites[i+1]['lat'], trip_sites[i+1]['lon'])
                total_driving += haversine(trip_sites[-1]['lat'], trip_sites[-1]['lon'],
                                          fly_out['lat'], fly_out['lon'])

            trip_plan = {
                'name': trip_def['name'],
                'description': trip_def['description'],
                'fly_in': trip_def['fly_in'],
                'fly_in_name': fly_in['name'],
                'fly_out': trip_def['fly_out'],
                'fly_out_name': fly_out['name'],
                'one_way_rental': trip_def['fly_in'] != trip_def['fly_out'],
                'recommended_days': trip_def['days'],
                'sites': trip_sites,
                'site_count': len(trip_sites),
                'total_driving_mi': round(total_driving, 0),
            }
            trip_plans.append(trip_plan)

    unassigned = [s for s in remaining_sites if s['name'] not in assigned_sites]

    print("\n" + "=" * 70)
    print("CONSOLIDATED TRIP SUMMARY")
    print("=" * 70)

    total_sites = sum(t['site_count'] for t in trip_plans)
    total_days = sum(t['recommended_days'] for t in trip_plans)

    for trip in trip_plans:
        rental_type = "ONE-WAY" if trip['one_way_rental'] else "round-trip"
        print(f"\n{trip['name']}")
        print(f"  {trip['fly_in']} → {trip['fly_out']} ({rental_type})")
        print(f"  {trip['recommended_days']} days, {trip['site_count']} sites, {trip['total_driving_mi']:.0f} mi")

    if unassigned:
        print(f"\n⚠️  UNASSIGNED SITES: {len(unassigned)}")
        for site in unassigned:
            print(f"  - {site['name']} ({site['city']}, {site['state']})")

    print(f"\n{'=' * 70}")
    print("FINAL SUMMARY")
    print(f"{'=' * 70}")
    print(f"Total trips: {len(trip_plans)}")
    print(f"Total sites: {total_sites}")
    print(f"Total days: {total_days}")
    print(f"Unassigned: {len(unassigned)}")
    print(f"Average sites/trip: {total_sites / len(trip_plans):.1f}")

    # Save outputs
    output_dir = Path("/workspace/3-route-planning/20251126")

    yaml_data = {
        'description': 'Consolidated regional airport trips (12 trips)',
        'total_trips': len(trip_plans),
        'total_sites': total_sites,
        'total_days': total_days,
        'trips': trip_plans,
        'unassigned_sites': unassigned if unassigned else None,
    }

    with open(output_dir / "airport_trips_consolidated.yaml", 'w') as f:
        yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False)

    print(f"\n✓ Saved to {output_dir / 'airport_trips_consolidated.yaml'}")

    # Create markdown summary
    md_lines = []
    md_lines.append("# Consolidated Regional NPS Trips (12 Trips)\n\n")
    md_lines.append(f"**Total Trips:** {len(trip_plans)} | **Total Sites:** {total_sites} | **Total Days:** {total_days}\n\n")
    md_lines.append("## Trip Summary\n\n")
    md_lines.append("| # | Trip | Fly In | Fly Out | Days | Sites | Driving |\n")
    md_lines.append("|---|------|--------|---------|------|-------|--------|\n")

    for i, trip in enumerate(trip_plans, 1):
        md_lines.append(f"| {i} | {trip['name']} | {trip['fly_in']} | {trip['fly_out']} | {trip['recommended_days']} | {trip['site_count']} | {trip['total_driving_mi']:.0f} mi |\n")

    md_lines.append("\n---\n\n")

    for trip in trip_plans:
        md_lines.append(f"## {trip['name']}\n\n")
        md_lines.append(f"*{trip['description']}*\n\n")
        md_lines.append(f"**{trip['fly_in']} → {trip['fly_out']}** | ")
        if trip['one_way_rental']:
            md_lines.append("ONE-WAY RENTAL | ")
        md_lines.append(f"**{trip['recommended_days']} days** | **{trip['site_count']} sites** | **{trip['total_driving_mi']:.0f} mi**\n\n")

        md_lines.append("| # | Site | Location |\n")
        md_lines.append("|---|------|----------|\n")
        for i, site in enumerate(trip['sites'], 1):
            md_lines.append(f"| {i} | {site['name']} | {site['city']}, {site['state']} |\n")
        md_lines.append("\n---\n\n")

    with open(output_dir / "consolidated_trips_summary.md", 'w') as f:
        f.writelines(md_lines)

    print(f"✓ Saved summary to {output_dir / 'consolidated_trips_summary.md'}")

    return trip_plans, unassigned


if __name__ == "__main__":
    main()
