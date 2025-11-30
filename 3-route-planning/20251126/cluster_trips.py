#!/usr/bin/env python3
"""
Create practical 2-day and 3-day trips from St. Louis using geographic clustering.

Instead of VRP (which optimizes for efficiency and creates single-day trips),
this creates realistic overnight trips by clustering sites by direction/region.

A 2-day trip:
- Day 1: Drive out, visit sites, stay overnight
- Day 2: Visit more sites, drive home

A 3-day trip:
- Day 1: Drive out, visit sites, stay overnight
- Day 2: Visit sites, stay overnight
- Day 3: Visit remaining sites, drive home
"""
import sys
sys.path.insert(0, '/workspace/src/routing')

import math
import yaml
from pathlib import Path
from collections import defaultdict
from nps_data_loader import NPSDataLoader

# St. Louis (Kirkwood) home base
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


def bearing(lat1, lon1, lat2, lon2):
    """Calculate bearing in degrees from point 1 to point 2"""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = math.atan2(x, y)
    return (math.degrees(bearing) + 360) % 360


def direction_name(bearing_deg):
    """Convert bearing to cardinal/intercardinal direction"""
    directions = [
        (22.5, "N"), (67.5, "NE"), (112.5, "E"), (157.5, "SE"),
        (202.5, "S"), (247.5, "SW"), (292.5, "W"), (337.5, "NW"), (360, "N")
    ]
    for limit, name in directions:
        if bearing_deg < limit:
            return name
    return "N"


def region_name(bearing_deg):
    """Group into 8 regions for clustering"""
    if bearing_deg < 22.5 or bearing_deg >= 337.5:
        return "North (Iowa)"
    elif bearing_deg < 67.5:
        return "Northeast (Chicago/Michigan)"
    elif bearing_deg < 112.5:
        return "East (Kentucky/Ohio)"
    elif bearing_deg < 157.5:
        return "Southeast (Tennessee/Alabama)"
    elif bearing_deg < 202.5:
        return "South (Mississippi)"
    elif bearing_deg < 247.5:
        return "Southwest (Arkansas/Oklahoma)"
    elif bearing_deg < 292.5:
        return "West (Kansas)"
    else:
        return "Northwest (Nebraska)"


def cluster_sites(sites_with_dist, max_distance):
    """Cluster sites by region and distance band"""
    regions = defaultdict(list)

    for name, site, dist in sites_with_dist:
        if dist > max_distance:
            continue
        b = bearing(HOME_LAT, HOME_LON, site.lat, site.lon)
        region = region_name(b)
        regions[region].append({
            'name': name,
            'lat': site.lat,
            'lon': site.lon,
            'city': site.city,
            'state': site.state,
            'dist_from_home': dist,
            'bearing': b,
            'direction': direction_name(b)
        })

    # Sort each region by distance
    for region in regions:
        regions[region].sort(key=lambda x: x['dist_from_home'])

    return regions


def create_2day_trips(regions):
    """
    Create 2-day trip plans from clustered regions.

    Strategy:
    - Group nearby sites in the same direction
    - Day 1: Drive to furthest point, visit sites along the way
    - Day 2: Visit remaining sites, return home
    - Max ~400 miles per day driving
    """
    trips = []
    trip_num = 1

    for region_name, sites in sorted(regions.items()):
        if not sites:
            continue

        # Group sites within 100 miles of each other
        remaining = sites.copy()

        while remaining:
            trip_sites = [remaining.pop(0)]  # Start with closest

            # Add nearby sites (within 100 miles of any trip site)
            changed = True
            while changed:
                changed = False
                for site in remaining[:]:
                    for trip_site in trip_sites:
                        dist = haversine(site['lat'], site['lon'],
                                        trip_site['lat'], trip_site['lon'])
                        if dist < 100:  # Within 100 miles of a trip site
                            trip_sites.append(site)
                            remaining.remove(site)
                            changed = True
                            break

            # Sort by distance from home
            trip_sites.sort(key=lambda x: x['dist_from_home'])

            # Calculate trip stats
            total_driving = 0
            furthest_dist = max(s['dist_from_home'] for s in trip_sites)

            # Estimate driving: home -> sites -> home
            # Simplified: furthest distance * 2 + 50% of inter-site driving
            inter_site_driving = 0
            for i in range(len(trip_sites) - 1):
                inter_site_driving += haversine(
                    trip_sites[i]['lat'], trip_sites[i]['lon'],
                    trip_sites[i+1]['lat'], trip_sites[i+1]['lon']
                )

            total_driving = furthest_dist * 2 + inter_site_driving

            # Determine if this is a day trip or overnight
            visit_time = len(trip_sites) * 2  # 2 hours per site
            driving_time = total_driving / 55  # 55 mph average
            total_hours = visit_time + driving_time

            if total_hours <= 12:
                trip_type = "Day Trip"
                days = 1
            elif total_hours <= 24:
                trip_type = "2-Day Overnight"
                days = 2
            else:
                trip_type = "2-Day Overnight (Long)"
                days = 2

            trip = {
                'trip_number': trip_num,
                'region': region_name,
                'type': trip_type,
                'days': days,
                'sites': trip_sites,
                'site_count': len(trip_sites),
                'furthest_distance_mi': round(furthest_dist, 1),
                'total_driving_mi': round(total_driving, 1),
                'estimated_driving_hours': round(driving_time, 1),
                'estimated_visit_hours': visit_time,
                'total_estimated_hours': round(total_hours, 1)
            }
            trips.append(trip)
            trip_num += 1

    return trips


def main():
    print("=" * 70)
    print("NPS TRIP CLUSTERING FROM ST. LOUIS")
    print("=" * 70)
    print(f"Home base: {HOME_NAME} ({HOME_LAT}, {HOME_LON})")
    print()

    # Load sites
    loader = NPSDataLoader()
    all_sites = loader.load_all_sites()

    # Calculate distances
    sites_with_dist = []
    for name, site in all_sites.items():
        dist = haversine(HOME_LAT, HOME_LON, site.lat, site.lon)
        sites_with_dist.append((name, site, dist))

    sites_with_dist.sort(key=lambda x: x[2])

    # Distance thresholds
    TWO_DAY_RADIUS = 440
    THREE_DAY_RADIUS = 660

    print("=" * 70)
    print("2-DAY TRIP PLANNING (within 440 miles)")
    print("=" * 70)

    # Cluster 2-day sites
    regions_2day = cluster_sites(sites_with_dist, TWO_DAY_RADIUS)

    print("\nSites by Region:")
    for region, sites in sorted(regions_2day.items()):
        print(f"\n  {region} ({len(sites)} sites):")
        for s in sites:
            print(f"    {s['dist_from_home']:6.1f} mi - {s['name']} ({s['city']}, {s['state']})")

    # Create trips
    trips_2day = create_2day_trips(regions_2day)

    print("\n" + "=" * 70)
    print("2-DAY TRIP PROPOSALS")
    print("=" * 70)

    for trip in trips_2day:
        print(f"\nTrip {trip['trip_number']}: {trip['region']} - {trip['type']}")
        print(f"  Sites: {trip['site_count']}")
        print(f"  Furthest point: {trip['furthest_distance_mi']} miles")
        print(f"  Total driving: {trip['total_driving_mi']} miles ({trip['estimated_driving_hours']} hours)")
        print(f"  Visit time: {trip['estimated_visit_hours']} hours")
        print(f"  Total time: {trip['total_estimated_hours']} hours")
        print("  Route:")
        for i, site in enumerate(trip['sites'], 1):
            print(f"    {i}. {site['name']} ({site['dist_from_home']:.0f} mi from home)")

    # Save 2-day trips
    output_dir = Path("/workspace/3-route-planning/20251126")

    trip_data_2day = {
        'home_base': {'name': HOME_NAME, 'lat': HOME_LAT, 'lon': HOME_LON},
        'max_distance': TWO_DAY_RADIUS,
        'trip_type': '2-day',
        'total_trips': len(trips_2day),
        'total_sites': sum(t['site_count'] for t in trips_2day),
        'trips': trips_2day
    }

    with open(output_dir / "2day_clustered_trips.yaml", 'w') as f:
        yaml.dump(trip_data_2day, f, default_flow_style=False, sort_keys=False)

    print(f"\n✓ Saved 2-day trips to {output_dir / '2day_clustered_trips.yaml'}")

    # Now handle 3-day trips (sites beyond 440 miles)
    print("\n" + "=" * 70)
    print("3-DAY TRIP PLANNING (440-660 miles)")
    print("=" * 70)

    # Get 3-day only sites
    three_day_only = [(n, s, d) for n, s, d in sites_with_dist
                      if TWO_DAY_RADIUS < d <= THREE_DAY_RADIUS]

    print(f"\n{len(three_day_only)} additional sites for 3-day trips:")
    regions_3day = cluster_sites(three_day_only, THREE_DAY_RADIUS)

    for region, sites in sorted(regions_3day.items()):
        if sites:
            print(f"\n  {region} ({len(sites)} sites):")
            for s in sites:
                print(f"    {s['dist_from_home']:6.1f} mi - {s['name']} ({s['city']}, {s['state']})")

    # Create 3-day trips
    trips_3day = []
    trip_num = 1

    for region_name, sites in sorted(regions_3day.items()):
        if not sites:
            continue

        # For 3-day trips, group sites in same region
        remaining = sites.copy()

        while remaining:
            trip_sites = [remaining.pop(0)]

            # Add nearby sites
            for site in remaining[:]:
                for trip_site in trip_sites:
                    dist = haversine(site['lat'], site['lon'],
                                    trip_site['lat'], trip_site['lon'])
                    if dist < 150:  # Wider radius for 3-day trips
                        trip_sites.append(site)
                        remaining.remove(site)
                        break

            trip_sites.sort(key=lambda x: x['dist_from_home'])

            # Calculate stats
            furthest_dist = max(s['dist_from_home'] for s in trip_sites)
            inter_site = sum(
                haversine(trip_sites[i]['lat'], trip_sites[i]['lon'],
                         trip_sites[i+1]['lat'], trip_sites[i+1]['lon'])
                for i in range(len(trip_sites) - 1)
            ) if len(trip_sites) > 1 else 0

            total_driving = furthest_dist * 2 + inter_site
            driving_hours = total_driving / 55
            visit_hours = len(trip_sites) * 2

            trips_3day.append({
                'trip_number': trip_num,
                'region': region_name,
                'type': '3-Day Overnight',
                'days': 3,
                'sites': trip_sites,
                'site_count': len(trip_sites),
                'furthest_distance_mi': round(furthest_dist, 1),
                'total_driving_mi': round(total_driving, 1),
                'estimated_driving_hours': round(driving_hours, 1),
                'estimated_visit_hours': visit_hours,
                'total_estimated_hours': round(driving_hours + visit_hours, 1)
            })
            trip_num += 1

    print("\n" + "=" * 70)
    print("3-DAY TRIP PROPOSALS")
    print("=" * 70)

    for trip in trips_3day:
        print(f"\nTrip {trip['trip_number']}: {trip['region']} - {trip['type']}")
        print(f"  Sites: {trip['site_count']}")
        print(f"  Furthest point: {trip['furthest_distance_mi']} miles")
        print(f"  Total driving: {trip['total_driving_mi']} miles ({trip['estimated_driving_hours']} hours)")
        print("  Route:")
        for i, site in enumerate(trip['sites'], 1):
            print(f"    {i}. {site['name']} ({site['dist_from_home']:.0f} mi from home)")

    # Save 3-day trips
    trip_data_3day = {
        'home_base': {'name': HOME_NAME, 'lat': HOME_LAT, 'lon': HOME_LON},
        'max_distance': THREE_DAY_RADIUS,
        'min_distance': TWO_DAY_RADIUS,
        'trip_type': '3-day',
        'total_trips': len(trips_3day),
        'total_sites': sum(t['site_count'] for t in trips_3day),
        'trips': trips_3day
    }

    with open(output_dir / "3day_clustered_trips.yaml", 'w') as f:
        yaml.dump(trip_data_3day, f, default_flow_style=False, sort_keys=False)

    print(f"\n✓ Saved 3-day trips to {output_dir / '3day_clustered_trips.yaml'}")

    # Summary
    total_2day_sites = sum(t['site_count'] for t in trips_2day)
    total_3day_sites = sum(t['site_count'] for t in trips_3day)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"2-Day Trips: {len(trips_2day)} trips covering {total_2day_sites} sites")
    print(f"3-Day Trips: {len(trips_3day)} trips covering {total_3day_sites} sites")
    print(f"Total: {len(trips_2day) + len(trips_3day)} trips, {total_2day_sites + total_3day_sites} sites")

    # Create checklist
    print("\n" + "=" * 70)
    print("CREATING CHECKLIST")
    print("=" * 70)

    checklist = []
    checklist.append("# NPS Sites from St. Louis - Trip Checklist\n")
    checklist.append(f"Home base: {HOME_NAME}\n")
    checklist.append(f"Generated: 2025-11-26\n\n")

    checklist.append("## 2-Day Trip Sites (within 440 miles)\n\n")
    for trip in trips_2day:
        checklist.append(f"### Trip {trip['trip_number']}: {trip['region']}\n")
        checklist.append(f"*{trip['type']} - {trip['total_driving_mi']} miles, ~{trip['total_estimated_hours']} hours*\n\n")
        for site in trip['sites']:
            checklist.append(f"- [ ] {site['name']} ({site['city']}, {site['state']}) - {site['dist_from_home']:.0f} mi\n")
        checklist.append("\n")

    checklist.append("\n## 3-Day Trip Sites (440-660 miles)\n\n")
    for trip in trips_3day:
        checklist.append(f"### Trip {trip['trip_number']}: {trip['region']}\n")
        checklist.append(f"*{trip['type']} - {trip['total_driving_mi']} miles, ~{trip['total_estimated_hours']} hours*\n\n")
        for site in trip['sites']:
            checklist.append(f"- [ ] {site['name']} ({site['city']}, {site['state']}) - {site['dist_from_home']:.0f} mi\n")
        checklist.append("\n")

    with open(output_dir / "trip_checklist.md", 'w') as f:
        f.writelines(checklist)

    print(f"✓ Saved checklist to {output_dir / 'trip_checklist.md'}")

    return trips_2day, trips_3day


if __name__ == "__main__":
    main()
