#!/usr/bin/env python3
"""
Create optimized 2-day and 3-day trips from St. Louis.

This version:
1. Manually combines single-site trips that can be done together
2. Groups trips by practical routes (en-route sites)
3. Focuses on maximizing sites per trip while staying within time limits
"""
import sys
sys.path.insert(0, '/workspace/src/routing')

import math
import yaml
from pathlib import Path
from nps_data_loader import NPSDataLoader

HOME_LAT = 38.5831
HOME_LON = -90.4068
HOME_NAME = "Kirkwood, MO"

def haversine(lat1, lon1, lat2, lon2):
    """Distance in miles"""
    R = 3959
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def get_site_data(loader, name):
    """Get site data with distance from home"""
    sites = loader.load_all_sites()
    if name in sites:
        site = sites[name]
        dist = haversine(HOME_LAT, HOME_LON, site.lat, site.lon)
        return {
            'name': name,
            'lat': site.lat,
            'lon': site.lon,
            'city': site.city,
            'state': site.state,
            'dist_from_home': round(dist, 1)
        }
    return None


def calculate_trip_stats(sites):
    """Calculate driving and time estimates for a trip"""
    if not sites:
        return {}

    # Get furthest site
    furthest = max(sites, key=lambda s: s['dist_from_home'])

    # Calculate inter-site driving
    inter_site = 0
    for i in range(len(sites) - 1):
        inter_site += haversine(
            sites[i]['lat'], sites[i]['lon'],
            sites[i+1]['lat'], sites[i+1]['lon']
        )

    # Total driving: home -> furthest -> home + inter-site
    total_driving = furthest['dist_from_home'] * 2 + inter_site
    driving_hours = total_driving / 55
    visit_hours = len(sites) * 2  # 2 hours per site
    total_hours = driving_hours + visit_hours

    return {
        'furthest_distance_mi': round(furthest['dist_from_home'], 1),
        'total_driving_mi': round(total_driving, 1),
        'estimated_driving_hours': round(driving_hours, 1),
        'estimated_visit_hours': visit_hours,
        'total_estimated_hours': round(total_hours, 1),
        'recommended_days': 1 if total_hours <= 12 else (2 if total_hours <= 24 else 3)
    }


def main():
    print("=" * 70)
    print("OPTIMIZED NPS TRIPS FROM ST. LOUIS")
    print("=" * 70)

    loader = NPSDataLoader()

    # Define optimized 2-day trips manually based on geographic analysis
    # These are practical routes that combine nearby sites

    two_day_trips = [
        {
            'name': 'Springfield Day Trip',
            'description': 'Quick day trip to Springfield, IL',
            'sites': ['Springfield 1908 Race Riot National Monument'],
            'type': 'Day Trip'
        },
        {
            'name': 'Indiana/Kentucky Loop',
            'description': 'George Rogers Clark + Lincoln Birthplace (en route)',
            'sites': ['George Rogers Clark NHP', 'Abraham Lincoln Birthplace NHP'],
            'type': '2-Day Overnight'
        },
        {
            'name': 'Ohio Heritage',
            'description': 'Cincinnati and Dayton sites',
            'sites': ['William Howard Taft NHS', 'Dayton Aviation Heritage NHP'],
            'type': '2-Day Overnight'
        },
        {
            'name': 'Northern Illinois/Chicago',
            'description': 'Chicago area including Pullman',
            'sites': ['Pullman NHP'],
            'type': 'Day Trip (Long)'
        },
        {
            'name': 'Iowa Heritage',
            'description': 'Herbert Hoover NHS',
            'sites': ['Herbert Hoover NHS'],
            'type': 'Day Trip (Long)'
        },
        {
            'name': 'Wisconsin Trail',
            'description': 'Ice Age National Scenic Trail',
            'sites': ['Ice Age National Scenic Trail'],
            'type': '2-Day Overnight'
        },
        {
            'name': 'Michigan Civil War',
            'description': 'River Raisin National Battlefield',
            'sites': ['River Raisin NBP'],
            'type': '2-Day Overnight'
        },
        {
            'name': 'Arkansas Northwest Loop',
            'description': 'Buffalo River, Pea Ridge, and Ft. Smith cluster',
            'sites': ['Buffalo NR', 'Pea Ridge NMP', 'Fort Smith NHS'],
            'type': '2-Day Overnight'
        },
        {
            'name': 'Arkansas Delta',
            'description': 'Arkansas Post and Little Rock',
            'sites': ['Arkansas Post N MEM', 'Little Rock Central High School NHS'],
            'type': '2-Day Overnight'
        },
        {
            'name': 'Tennessee Civil War',
            'description': 'Fort Donelson and Stones River battlefields',
            'sites': ['Fort Donelson NB', 'Stones River NB'],
            'type': '2-Day Overnight'
        },
        {
            'name': 'Great Smokies Region',
            'description': 'Big South Fork, Obed, and approaches to Smokies',
            'sites': ['Big South Fork NRRA', 'Obed WSR', 'Great Smoky Mountains NP'],
            'type': '2-Day Overnight (Long)'
        },
        {
            'name': 'Alabama Civil Rights',
            'description': 'Birmingham and Anniston civil rights sites',
            'sites': ['Birmingham Civil Rights NM', 'Freedom Riders NM'],
            'type': '2-Day Overnight (Long)'
        },
        {
            'name': 'Mississippi Delta',
            'description': 'Emmett Till memorial',
            'sites': ['Emmett Till and Mamie Till-Mobley NM'],
            'type': '2-Day Overnight'
        },
        {
            'name': 'Mississippi Jackson',
            'description': 'Medgar Evers Home',
            'sites': ['Medgar and Myrlie Evers Home NM'],
            'type': '2-Day Overnight (Long)'
        },
        {
            'name': 'Kansas City Area',
            'description': 'Truman NHS and Fort Scott',
            'sites': ['Harry S Truman NHS', 'Fort Scott NHS'],
            'type': '2-Day Overnight'
        },
        {
            'name': 'Nebraska Homestead',
            'description': 'Homestead National Historical Park',
            'sites': ['Homestead NHP'],
            'type': '2-Day Overnight'
        },
        {
            'name': 'West Virginia Rafting',
            'description': 'Gauley River NRA',
            'sites': ['Gauley River NRA'],
            'type': '2-Day Overnight (Long)'
        }
    ]

    three_day_trips = [
        {
            'name': 'Oklahoma Loop',
            'description': 'Oklahoma City Memorial and Chickasaw NRA',
            'sites': ['Oklahoma City N MEM', 'Chickasaw NRA'],
            'type': '3-Day Overnight'
        },
        {
            'name': 'Minnesota Twin Cities',
            'description': 'Mississippi NRRA in St. Paul',
            'sites': ['Mississippi NRRA'],
            'type': '3-Day Overnight'
        },
        {
            'name': 'Minnesota Pipestone',
            'description': 'Pipestone National Monument',
            'sites': ['Pipestone NM'],
            'type': '3-Day Overnight'
        },
        {
            'name': 'Upper Peninsula Michigan',
            'description': 'Pictured Rocks, Isle Royale, Keweenaw',
            'sites': ['Pictured Rocks NL', 'Isle Royale NP', 'Keweenaw NHP'],
            'type': '3-Day Overnight (Long)'
        },
        {
            'name': 'Lake Superior Loop',
            'description': 'Apostle Islands and Grand Portage',
            'sites': ['Apostle Islands NL', 'Grand Portage NM'],
            'type': '3-Day Overnight'
        },
        {
            'name': 'Michigan Lakeshores',
            'description': 'Sleeping Bear Dunes',
            'sites': ['Sleeping Bear Dunes NL'],
            'type': '3-Day Overnight'
        },
        {
            'name': 'Ohio Valley Heritage',
            'description': 'Cuyahoga Valley and First Ladies NHS',
            'sites': ['Cuyahoga Valley NP', 'First Ladies NHS'],
            'type': '3-Day Overnight'
        },
        {
            'name': 'Pennsylvania 9/11 Memorial',
            'description': 'Flight 93 and Friendship Hill',
            'sites': ['Flight 93 N MEM', 'Friendship Hill NHS'],
            'type': '3-Day Overnight'
        },
        {
            'name': 'Appalachian Virginia',
            'description': 'Cedar Creek, Bluestone, Andrew Johnson',
            'sites': ['Cedar Creek and Belle Grove NHP', 'Bluestone NSR', 'Andrew Johnson NHS'],
            'type': '3-Day Overnight (Long)'
        },
        {
            'name': 'Georgia Atlanta Area',
            'description': 'MLK, Chattahoochee River NRA',
            'sites': ['Martin Luther King, Jr NHP', 'Chattahoochee River NRA'],
            'type': '3-Day Overnight'
        },
        {
            'name': 'Georgia/Alabama Tuskegee',
            'description': 'Tuskegee Airmen and Institute',
            'sites': ['Tuskegee Airmen NHS', 'Tuskegee Institute NHS'],
            'type': '3-Day Overnight'
        },
        {
            'name': 'Georgia Jimmy Carter',
            'description': 'Jimmy Carter NHP and Ocmulgee',
            'sites': ['Jimmy Carter NHP', 'Ocmulgee NHP'],
            'type': '3-Day Overnight'
        },
        {
            'name': 'Carolinas Revolutionary',
            'description': 'Cowpens, Ninety Six, Guilford Courthouse',
            'sites': ['Cowpens NB', 'Ninety Six NHS', 'Guilford Courthouse NMP'],
            'type': '3-Day Overnight (Long)'
        },
        {
            'name': 'Carolina Carl Sandburg',
            'description': 'Carl Sandburg Home',
            'sites': ['Carl Sandburg Home NHS'],
            'type': '3-Day Overnight'
        },
        {
            'name': 'Louisiana New Orleans',
            'description': 'New Orleans Jazz NHP',
            'sites': ['New Orleans Jazz NHP'],
            'type': '3-Day Overnight'
        },
        {
            'name': 'Mississippi/Louisiana Natchez',
            'description': 'Natchez NHP and Cane River',
            'sites': ['Natchez NHP', 'Cane River Creole NHP'],
            'type': '3-Day Overnight'
        },
        {
            'name': 'Gulf Coast',
            'description': 'Gulf Islands National Seashore',
            'sites': ['Gulf Islands NS'],
            'type': '3-Day Overnight'
        },
        {
            'name': 'Kansas Fort Larned',
            'description': 'Fort Larned NHS',
            'sites': ['Fort Larned NHS'],
            'type': '3-Day Overnight'
        },
        {
            'name': 'Colorado Amache',
            'description': 'Amache NHS',
            'sites': ['Amache NHS'],
            'type': '3-Day Overnight (Long)'
        },
        {
            'name': 'Texas Panhandle',
            'description': 'Lake Meredith NRA',
            'sites': ['Lake Meredith NRA'],
            'type': '3-Day Overnight (Long)'
        }
    ]

    # Process 2-day trips
    print("\n" + "=" * 70)
    print("2-DAY TRIPS")
    print("=" * 70)

    processed_2day = []
    for i, trip in enumerate(two_day_trips, 1):
        sites = []
        for site_name in trip['sites']:
            site_data = get_site_data(loader, site_name)
            if site_data:
                sites.append(site_data)
            else:
                print(f"  Warning: Could not find site '{site_name}'")

        if sites:
            stats = calculate_trip_stats(sites)
            processed_trip = {
                'trip_number': i,
                'name': trip['name'],
                'description': trip['description'],
                'type': trip['type'],
                'site_count': len(sites),
                'sites': sites,
                **stats
            }
            processed_2day.append(processed_trip)

            print(f"\nTrip {i}: {trip['name']}")
            print(f"  Type: {trip['type']}")
            print(f"  Sites: {len(sites)}")
            print(f"  Furthest: {stats['furthest_distance_mi']} mi")
            print(f"  Total driving: {stats['total_driving_mi']} mi ({stats['estimated_driving_hours']}h)")
            print(f"  Visit time: {stats['estimated_visit_hours']}h")
            print(f"  Total: {stats['total_estimated_hours']}h")
            for site in sites:
                print(f"    - {site['name']} ({site['dist_from_home']} mi)")

    # Process 3-day trips
    print("\n" + "=" * 70)
    print("3-DAY TRIPS")
    print("=" * 70)

    processed_3day = []
    for i, trip in enumerate(three_day_trips, 1):
        sites = []
        for site_name in trip['sites']:
            site_data = get_site_data(loader, site_name)
            if site_data:
                sites.append(site_data)
            else:
                print(f"  Warning: Could not find site '{site_name}'")

        if sites:
            stats = calculate_trip_stats(sites)
            processed_trip = {
                'trip_number': i,
                'name': trip['name'],
                'description': trip['description'],
                'type': trip['type'],
                'site_count': len(sites),
                'sites': sites,
                **stats
            }
            processed_3day.append(processed_trip)

            print(f"\nTrip {i}: {trip['name']}")
            print(f"  Type: {trip['type']}")
            print(f"  Sites: {len(sites)}")
            print(f"  Furthest: {stats['furthest_distance_mi']} mi")
            print(f"  Total driving: {stats['total_driving_mi']} mi ({stats['estimated_driving_hours']}h)")
            print(f"  Visit time: {stats['estimated_visit_hours']}h")
            print(f"  Total: {stats['total_estimated_hours']}h")
            for site in sites:
                print(f"    - {site['name']} ({site['dist_from_home']} mi)")

    # Save YAML files
    output_dir = Path("/workspace/3-route-planning/20251126")

    yaml_2day = {
        'home_base': {'name': HOME_NAME, 'lat': HOME_LAT, 'lon': HOME_LON},
        'trip_type': '2-day optimized',
        'total_trips': len(processed_2day),
        'total_sites': sum(t['site_count'] for t in processed_2day),
        'trips': processed_2day
    }

    yaml_3day = {
        'home_base': {'name': HOME_NAME, 'lat': HOME_LAT, 'lon': HOME_LON},
        'trip_type': '3-day optimized',
        'total_trips': len(processed_3day),
        'total_sites': sum(t['site_count'] for t in processed_3day),
        'trips': processed_3day
    }

    with open(output_dir / "2day_optimized_trips.yaml", 'w') as f:
        yaml.dump(yaml_2day, f, default_flow_style=False, sort_keys=False)

    with open(output_dir / "3day_optimized_trips.yaml", 'w') as f:
        yaml.dump(yaml_3day, f, default_flow_style=False, sort_keys=False)

    print(f"\n✓ Saved to {output_dir / '2day_optimized_trips.yaml'}")
    print(f"✓ Saved to {output_dir / '3day_optimized_trips.yaml'}")

    # Create optimized checklist
    print("\n" + "=" * 70)
    print("CREATING OPTIMIZED CHECKLIST")
    print("=" * 70)

    checklist = []
    checklist.append("# NPS Sites from St. Louis - Optimized Trip Checklist\n\n")
    checklist.append(f"**Home base:** {HOME_NAME}\n\n")
    checklist.append(f"**Generated:** 2025-11-26\n\n")

    checklist.append("---\n\n")
    checklist.append("## 2-Day Trip Sites\n\n")

    for trip in processed_2day:
        checklist.append(f"### {trip['name']}\n")
        checklist.append(f"*{trip['type']} | {trip['total_driving_mi']} mi driving | ~{trip['total_estimated_hours']}h total*\n\n")
        checklist.append(f"_{trip['description']}_\n\n")
        for site in trip['sites']:
            checklist.append(f"- [ ] **{site['name']}** ({site['city']}, {site['state']}) - {site['dist_from_home']} mi from home\n")
        checklist.append("\n")

    checklist.append("---\n\n")
    checklist.append("## 3-Day Trip Sites\n\n")

    for trip in processed_3day:
        checklist.append(f"### {trip['name']}\n")
        checklist.append(f"*{trip['type']} | {trip['total_driving_mi']} mi driving | ~{trip['total_estimated_hours']}h total*\n\n")
        checklist.append(f"_{trip['description']}_\n\n")
        for site in trip['sites']:
            checklist.append(f"- [ ] **{site['name']}** ({site['city']}, {site['state']}) - {site['dist_from_home']} mi from home\n")
        checklist.append("\n")

    # Summary
    total_2day = sum(t['site_count'] for t in processed_2day)
    total_3day = sum(t['site_count'] for t in processed_3day)

    checklist.append("---\n\n")
    checklist.append("## Summary\n\n")
    checklist.append(f"- **2-Day Trips:** {len(processed_2day)} trips covering {total_2day} sites\n")
    checklist.append(f"- **3-Day Trips:** {len(processed_3day)} trips covering {total_3day} sites\n")
    checklist.append(f"- **Total:** {len(processed_2day) + len(processed_3day)} trips, {total_2day + total_3day} sites\n")

    with open(output_dir / "optimized_trip_checklist.md", 'w') as f:
        f.writelines(checklist)

    print(f"✓ Saved checklist to {output_dir / 'optimized_trip_checklist.md'}")

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"2-Day Trips: {len(processed_2day)} trips covering {total_2day} sites")
    print(f"3-Day Trips: {len(processed_3day)} trips covering {total_3day} sites")
    print(f"Total: {len(processed_2day) + len(processed_3day)} trips, {total_2day + total_3day} sites")


if __name__ == "__main__":
    main()
