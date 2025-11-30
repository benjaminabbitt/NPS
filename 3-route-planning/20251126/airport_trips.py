#!/usr/bin/env python3
"""
Plan airport-based trips for NPS sites NOT covered by St. Louis 2/3-day trips.

This identifies remaining lower-48 sites and clusters them by major airports
for fly-in/fly-out trip planning.
"""
import sys
sys.path.insert(0, '/workspace/src/routing')

import math
import yaml
from pathlib import Path
from collections import defaultdict
from nps_data_loader import NPSDataLoader

# Sites already covered by St. Louis trips (extracted from YAML files)
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

# Major airports with coordinates for trip planning
MAJOR_AIRPORTS = {
    # West Coast
    'SEA': {'name': 'Seattle-Tacoma (SEA)', 'lat': 47.4502, 'lon': -122.3088, 'city': 'Seattle', 'state': 'WA'},
    'PDX': {'name': 'Portland (PDX)', 'lat': 45.5898, 'lon': -122.5951, 'city': 'Portland', 'state': 'OR'},
    'SFO': {'name': 'San Francisco (SFO)', 'lat': 37.6213, 'lon': -122.3790, 'city': 'San Francisco', 'state': 'CA'},
    'LAX': {'name': 'Los Angeles (LAX)', 'lat': 33.9425, 'lon': -118.4081, 'city': 'Los Angeles', 'state': 'CA'},
    'SAN': {'name': 'San Diego (SAN)', 'lat': 32.7336, 'lon': -117.1897, 'city': 'San Diego', 'state': 'CA'},

    # Southwest
    'PHX': {'name': 'Phoenix (PHX)', 'lat': 33.4373, 'lon': -112.0078, 'city': 'Phoenix', 'state': 'AZ'},
    'LAS': {'name': 'Las Vegas (LAS)', 'lat': 36.0840, 'lon': -115.1537, 'city': 'Las Vegas', 'state': 'NV'},
    'ABQ': {'name': 'Albuquerque (ABQ)', 'lat': 35.0402, 'lon': -106.6090, 'city': 'Albuquerque', 'state': 'NM'},
    'ELP': {'name': 'El Paso (ELP)', 'lat': 31.8072, 'lon': -106.3778, 'city': 'El Paso', 'state': 'TX'},

    # Mountain/Plains
    'DEN': {'name': 'Denver (DEN)', 'lat': 39.8561, 'lon': -104.6737, 'city': 'Denver', 'state': 'CO'},
    'SLC': {'name': 'Salt Lake City (SLC)', 'lat': 40.7899, 'lon': -111.9791, 'city': 'Salt Lake City', 'state': 'UT'},
    'BOI': {'name': 'Boise (BOI)', 'lat': 43.5644, 'lon': -116.2228, 'city': 'Boise', 'state': 'ID'},
    'BIL': {'name': 'Billings (BIL)', 'lat': 45.8077, 'lon': -108.5430, 'city': 'Billings', 'state': 'MT'},
    'RAP': {'name': 'Rapid City (RAP)', 'lat': 44.0453, 'lon': -103.0574, 'city': 'Rapid City', 'state': 'SD'},

    # Texas
    'DFW': {'name': 'Dallas-Fort Worth (DFW)', 'lat': 32.8998, 'lon': -97.0403, 'city': 'Dallas', 'state': 'TX'},
    'IAH': {'name': 'Houston (IAH)', 'lat': 29.9902, 'lon': -95.3368, 'city': 'Houston', 'state': 'TX'},
    'SAT': {'name': 'San Antonio (SAT)', 'lat': 29.5337, 'lon': -98.4698, 'city': 'San Antonio', 'state': 'TX'},
    'AUS': {'name': 'Austin (AUS)', 'lat': 30.1975, 'lon': -97.6664, 'city': 'Austin', 'state': 'TX'},

    # Northeast
    'BOS': {'name': 'Boston (BOS)', 'lat': 42.3656, 'lon': -71.0096, 'city': 'Boston', 'state': 'MA'},
    'JFK': {'name': 'New York JFK (JFK)', 'lat': 40.6413, 'lon': -73.7781, 'city': 'New York', 'state': 'NY'},
    'EWR': {'name': 'Newark (EWR)', 'lat': 40.6895, 'lon': -74.1745, 'city': 'Newark', 'state': 'NJ'},
    'PHL': {'name': 'Philadelphia (PHL)', 'lat': 39.8744, 'lon': -75.2424, 'city': 'Philadelphia', 'state': 'PA'},
    'DCA': {'name': 'Washington Reagan (DCA)', 'lat': 38.8512, 'lon': -77.0402, 'city': 'Washington', 'state': 'DC'},
    'IAD': {'name': 'Washington Dulles (IAD)', 'lat': 38.9531, 'lon': -77.4565, 'city': 'Washington', 'state': 'DC'},

    # Southeast
    'CLT': {'name': 'Charlotte (CLT)', 'lat': 35.2140, 'lon': -80.9431, 'city': 'Charlotte', 'state': 'NC'},
    'RDU': {'name': 'Raleigh-Durham (RDU)', 'lat': 35.8801, 'lon': -78.7880, 'city': 'Raleigh', 'state': 'NC'},
    'MIA': {'name': 'Miami (MIA)', 'lat': 25.7959, 'lon': -80.2870, 'city': 'Miami', 'state': 'FL'},
    'TPA': {'name': 'Tampa (TPA)', 'lat': 27.9756, 'lon': -82.5333, 'city': 'Tampa', 'state': 'FL'},
    'MCO': {'name': 'Orlando (MCO)', 'lat': 28.4312, 'lon': -81.3081, 'city': 'Orlando', 'state': 'FL'},
    'JAX': {'name': 'Jacksonville (JAX)', 'lat': 30.4941, 'lon': -81.6879, 'city': 'Jacksonville', 'state': 'FL'},

    # Additional regional
    'RNO': {'name': 'Reno (RNO)', 'lat': 39.4991, 'lon': -119.7681, 'city': 'Reno', 'state': 'NV'},
    'FAT': {'name': 'Fresno (FAT)', 'lat': 36.7762, 'lon': -119.7181, 'city': 'Fresno', 'state': 'CA'},
    'SMF': {'name': 'Sacramento (SMF)', 'lat': 38.6954, 'lon': -121.5910, 'city': 'Sacramento', 'state': 'CA'},
}

# Exclude non-lower-48 states
EXCLUDED_STATES = {'Alaska', 'Hawaii', 'AK', 'HI', 'Puerto Rico', 'PR',
                   'Virgin Islands', 'VI', 'Guam', 'GU', 'American Samoa', 'AS'}


def haversine(lat1, lon1, lat2, lon2):
    """Distance in miles"""
    R = 3959
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def find_nearest_airport(lat, lon):
    """Find the nearest major airport to a location"""
    nearest = None
    min_dist = float('inf')

    for code, airport in MAJOR_AIRPORTS.items():
        dist = haversine(lat, lon, airport['lat'], airport['lon'])
        if dist < min_dist:
            min_dist = dist
            nearest = code

    return nearest, min_dist


def main():
    print("=" * 70)
    print("AIRPORT-BASED TRIP PLANNING")
    print("For NPS sites NOT covered by St. Louis trips")
    print("=" * 70)

    # Load all sites
    loader = NPSDataLoader()
    all_sites = loader.load_all_sites()

    print(f"\nTotal sites in database: {len(all_sites)}")
    print(f"Sites covered by St. Louis trips: {len(STL_COVERED_SITES)}")

    # Find remaining lower-48 sites
    remaining_sites = []
    excluded_sites = []

    for name, site in all_sites.items():
        # Skip St. Louis covered sites
        if name in STL_COVERED_SITES:
            continue

        # Skip non-lower-48
        if site.state in EXCLUDED_STATES:
            excluded_sites.append((name, site.state))
            continue

        # Find nearest airport
        nearest_airport, dist_to_airport = find_nearest_airport(site.lat, site.lon)

        remaining_sites.append({
            'name': name,
            'lat': site.lat,
            'lon': site.lon,
            'city': site.city,
            'state': site.state,
            'nearest_airport': nearest_airport,
            'dist_to_airport': round(dist_to_airport, 1)
        })

    print(f"Remaining lower-48 sites: {len(remaining_sites)}")
    print(f"Excluded (AK/HI/territories): {len(excluded_sites)}")

    if excluded_sites:
        print("\n  Excluded sites:")
        for name, state in excluded_sites:
            print(f"    - {name} ({state})")

    # Group by nearest airport
    airport_clusters = defaultdict(list)
    for site in remaining_sites:
        airport_clusters[site['nearest_airport']].append(site)

    # Sort sites within each cluster by distance to airport
    for airport in airport_clusters:
        airport_clusters[airport].sort(key=lambda x: x['dist_to_airport'])

    print("\n" + "=" * 70)
    print("SITES BY NEAREST AIRPORT")
    print("=" * 70)

    # Sort airports by number of sites (descending)
    sorted_airports = sorted(airport_clusters.items(),
                            key=lambda x: len(x[1]), reverse=True)

    for airport_code, sites in sorted_airports:
        airport = MAJOR_AIRPORTS[airport_code]
        print(f"\n{airport['name']} - {len(sites)} sites")
        print("-" * 50)
        for site in sites:
            print(f"  {site['dist_to_airport']:5.0f} mi - {site['name']} ({site['city']}, {site['state']})")

    # Create trip plans by airport
    print("\n" + "=" * 70)
    print("AIRPORT TRIP PLANNING")
    print("=" * 70)

    trip_plans = []

    for airport_code, sites in sorted_airports:
        if not sites:
            continue

        airport = MAJOR_AIRPORTS[airport_code]

        # Group sites into logical trips based on distance and clustering
        remaining = sites.copy()
        trip_num = 1

        while remaining:
            # Start with closest site to airport
            trip_sites = [remaining.pop(0)]

            # Add nearby sites (within 150 miles of any trip site)
            changed = True
            while changed and remaining:
                changed = False
                for site in remaining[:]:
                    for trip_site in trip_sites:
                        dist = haversine(site['lat'], site['lon'],
                                        trip_site['lat'], trip_site['lon'])
                        if dist < 150:
                            trip_sites.append(site)
                            remaining.remove(site)
                            changed = True
                            break

            # Calculate trip stats
            if trip_sites:
                max_dist = max(s['dist_to_airport'] for s in trip_sites)

                # Estimate driving
                inter_site = 0
                for i in range(len(trip_sites) - 1):
                    inter_site += haversine(
                        trip_sites[i]['lat'], trip_sites[i]['lon'],
                        trip_sites[i+1]['lat'], trip_sites[i+1]['lon']
                    )

                total_driving = max_dist * 2 + inter_site
                driving_hours = total_driving / 55
                visit_hours = len(trip_sites) * 2
                total_hours = driving_hours + visit_hours

                # Determine trip length
                if total_hours <= 12:
                    trip_type = "Day Trip"
                    days = 1
                elif total_hours <= 24:
                    trip_type = "2-Day Trip"
                    days = 2
                elif total_hours <= 36:
                    trip_type = "3-Day Trip"
                    days = 3
                else:
                    trip_type = "4+ Day Trip"
                    days = max(4, int(total_hours / 10))

                trip_plan = {
                    'airport_code': airport_code,
                    'airport_name': airport['name'],
                    'trip_number': trip_num,
                    'type': trip_type,
                    'recommended_days': days,
                    'sites': trip_sites,
                    'site_count': len(trip_sites),
                    'max_dist_from_airport': max_dist,
                    'total_driving_mi': round(total_driving, 1),
                    'estimated_driving_hours': round(driving_hours, 1),
                    'estimated_visit_hours': visit_hours,
                    'total_estimated_hours': round(total_hours, 1)
                }
                trip_plans.append(trip_plan)
                trip_num += 1

    # Group trips by airport for output
    trips_by_airport = defaultdict(list)
    for trip in trip_plans:
        trips_by_airport[trip['airport_code']].append(trip)

    # Print trip plans
    total_sites_planned = 0
    for airport_code in [a[0] for a in sorted_airports]:
        if airport_code not in trips_by_airport:
            continue

        trips = trips_by_airport[airport_code]
        airport = MAJOR_AIRPORTS[airport_code]

        print(f"\n{'=' * 70}")
        print(f"FLY INTO: {airport['name']}")
        print(f"{'=' * 70}")

        for trip in trips:
            total_sites_planned += trip['site_count']
            print(f"\nTrip {trip['trip_number']}: {trip['type']} ({trip['recommended_days']} days)")
            print(f"  Sites: {trip['site_count']}")
            print(f"  Max distance from airport: {trip['max_dist_from_airport']:.0f} mi")
            print(f"  Total driving: {trip['total_driving_mi']:.0f} mi ({trip['estimated_driving_hours']:.1f}h)")
            print(f"  Visit time: {trip['estimated_visit_hours']}h")
            print(f"  Total time: {trip['total_estimated_hours']:.1f}h")
            print("  Sites:")
            for site in trip['sites']:
                print(f"    - {site['name']} ({site['city']}, {site['state']}) - {site['dist_to_airport']:.0f} mi from airport")

    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    print(f"Total airports used: {len(trips_by_airport)}")
    print(f"Total trips: {len(trip_plans)}")
    print(f"Total sites planned: {total_sites_planned}")

    # Save to YAML
    output_dir = Path("/workspace/3-route-planning/20251126")

    yaml_data = {
        'description': 'Airport-based trips for NPS sites not covered by St. Louis trips',
        'stl_covered_count': len(STL_COVERED_SITES),
        'remaining_sites_count': len(remaining_sites),
        'total_trips': len(trip_plans),
        'airports_used': len(trips_by_airport),
        'trips_by_airport': {}
    }

    for airport_code, trips in trips_by_airport.items():
        airport = MAJOR_AIRPORTS[airport_code]
        yaml_data['trips_by_airport'][airport_code] = {
            'airport_name': airport['name'],
            'airport_city': airport['city'],
            'airport_state': airport['state'],
            'airport_lat': airport['lat'],
            'airport_lon': airport['lon'],
            'trip_count': len(trips),
            'trips': trips
        }

    with open(output_dir / "airport_trips.yaml", 'w') as f:
        yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False)

    print(f"\n✓ Saved to {output_dir / 'airport_trips.yaml'}")

    # Create checklist
    checklist = []
    checklist.append("# Airport-Based NPS Trip Checklist\n\n")
    checklist.append("**For sites NOT covered by St. Louis 2/3-day trips**\n\n")
    checklist.append(f"**Generated:** 2025-11-26\n\n")
    checklist.append("---\n\n")

    for airport_code in [a[0] for a in sorted_airports]:
        if airport_code not in trips_by_airport:
            continue

        trips = trips_by_airport[airport_code]
        airport = MAJOR_AIRPORTS[airport_code]

        checklist.append(f"## Fly Into: {airport['name']}\n\n")

        for trip in trips:
            checklist.append(f"### Trip {trip['trip_number']}: {trip['type']}\n")
            checklist.append(f"*{trip['recommended_days']} days | {trip['total_driving_mi']:.0f} mi driving | ~{trip['total_estimated_hours']:.0f}h total*\n\n")
            for site in trip['sites']:
                checklist.append(f"- [ ] **{site['name']}** ({site['city']}, {site['state']}) - {site['dist_to_airport']:.0f} mi from airport\n")
            checklist.append("\n")

        checklist.append("---\n\n")

    # Summary
    checklist.append("## Summary\n\n")
    checklist.append(f"- **Airports:** {len(trips_by_airport)}\n")
    checklist.append(f"- **Total Trips:** {len(trip_plans)}\n")
    checklist.append(f"- **Total Sites:** {total_sites_planned}\n")
    checklist.append(f"\n*Note: {len(STL_COVERED_SITES)} sites are covered by St. Louis 2/3-day trips*\n")

    with open(output_dir / "airport_trip_checklist.md", 'w') as f:
        f.writelines(checklist)

    print(f"✓ Saved checklist to {output_dir / 'airport_trip_checklist.md'}")

    return trip_plans


if __name__ == "__main__":
    main()
