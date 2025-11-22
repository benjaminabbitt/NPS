#!/usr/bin/env python3
"""
Demo: Route 10 NPS Sites
Using known coordinates from the first 10 sites in Chroma
"""

import json
import math
from typing import List, Tuple
from dataclasses import dataclass


# Hardcoded coordinates for demo (first 10 sites from Chroma)
SITE_COORDS = {
    "Abraham Lincoln Birthplace NHP": (37.5357, -85.7433, "Hodgenville", "KY"),
    "Acadia NP": (44.3386, -68.2733, "Bar Harbor", "ME"),
    "Adams NHP": (42.2529, -71.0023, "Quincy", "MA"),
    "African American Civil War MEM": (38.8921, -77.0241, "Washington", "DC"),
    "African Burial Ground NM": (40.7145, -74.0048, "New York", "NY"),
    "Agate Fossil Beds NM": (42.4187, -103.7272, "Harrison", "NE"),
    "Alagnak WR": (59.0725, -156.8493, "King Salmon", "AK"),
    "Alcatraz Island": (37.8267, -122.4230, "San Francisco", "CA"),
    "Aleutian World War II NHA": (53.8845, -166.5546, "Unalaska", "AK"),
    "Alibates Flint Quarries NM": (35.5665, -101.6772, "Fritch", "TX"),
}


@dataclass
class Site:
    """NPS Site with location"""
    name: str
    state: str
    city: str
    lat: float
    lon: float
    visit_duration_hours: float = 2.0

    def __repr__(self):
        return f"{self.name} ({self.city}, {self.state})"


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in miles"""
    R = 3959
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def nearest_neighbor_route(sites: List[Site], start_index: int = 0) -> List[Site]:
    """Simple nearest neighbor heuristic for TSP"""
    unvisited = set(range(len(sites)))
    route = []
    current = start_index

    while unvisited:
        route.append(sites[current])
        unvisited.discard(current)

        if not unvisited:
            break

        # Find nearest unvisited site
        min_dist = float('inf')
        nearest = None

        for idx in unvisited:
            dist = haversine_distance(
                sites[current].lat, sites[current].lon,
                sites[idx].lat, sites[idx].lon
            )
            if dist < min_dist:
                min_dist = dist
                nearest = idx

        current = nearest

    return route


def calculate_trip_stats(route: List[Site], start_loc: Tuple[float, float]) -> dict:
    """Calculate comprehensive trip statistics"""
    total_distance = 0
    current_lat, current_lon = start_loc
    segments = []

    for i, site in enumerate(route):
        dist = haversine_distance(current_lat, current_lon, site.lat, site.lon)
        total_distance += dist

        if i < len(route) - 1:
            next_site = route[i + 1]
            next_dist = haversine_distance(site.lat, site.lon, next_site.lat, next_site.lon)
            segments.append({
                'from': str(site),
                'to': str(next_site),
                'distance_miles': round(next_dist, 1),
                'drive_hours': round(next_dist / 55.0, 1)
            })

        current_lat, current_lon = site.lat, site.lon

    # Return to start
    return_dist = haversine_distance(current_lat, current_lon, start_loc[0], start_loc[1])
    total_distance += return_dist

    total_drive_hours = total_distance / 55.0
    total_visit_hours = sum(s.visit_duration_hours for s in route)

    return {
        'total_distance_miles': round(total_distance, 1),
        'total_drive_hours': round(total_drive_hours, 1),
        'total_visit_hours': round(total_visit_hours, 1),
        'total_trip_hours': round(total_drive_hours + total_visit_hours, 1),
        'site_count': len(route),
        'segments': segments
    }


def main():
    print("="*70)
    print("Route 10 NPS Sites - Minimum Travel Time Demo")
    print("="*70)

    # Create sites from hardcoded data
    sites = []
    for name, (lat, lon, city, state) in SITE_COORDS.items():
        sites.append(Site(
            name=name,
            lat=lat,
            lon=lon,
            city=city,
            state=state
        ))

    print(f"\nLoaded {len(sites)} sites:\n")
    for i, site in enumerate(sites, 1):
        print(f"  {i}. {site}")

    # Use first site as starting point
    start_loc = (sites[0].lat, sites[0].lon)
    print(f"\nStart location: {sites[0]}\n")

    # Find optimal route
    print("Optimizing route using nearest neighbor algorithm...")
    optimized_route = nearest_neighbor_route(sites, start_index=0)

    # Calculate stats
    stats = calculate_trip_stats(optimized_route, start_loc)

    print(f"\n{'='*70}")
    print("OPTIMIZED ROUTE SUMMARY")
    print(f"{'='*70}")
    print(f"\nTrip Statistics:")
    print(f"  Sites visited: {stats['site_count']}")
    print(f"  Total distance: {stats['total_distance_miles']:,} miles")
    print(f"  Total driving time: {stats['total_drive_hours']:.1f} hours")
    print(f"  Total visit time: {stats['total_visit_hours']:.1f} hours")
    print(f"  Total trip time: {stats['total_trip_hours']:.1f} hours")
    print(f"  Estimated days: {max(1, int(stats['total_trip_hours'] / 12))} days")

    print(f"\n\nOptimized Route Order:")
    for i, site in enumerate(optimized_route, 1):
        print(f"  {i}. {site}")

    print(f"\n\nDriving Segments:")
    for seg in stats['segments']:
        print(f"  • {seg['distance_miles']} mi ({seg['drive_hours']} hrs)")
        print(f"    {seg['from']} → {seg['to']}")

    # Save to JSON
    result = {
        'algorithm': 'nearest_neighbor_heuristic',
        'description': 'Routes 10 NPS sites to minimize total travel distance',
        'start_location': str(sites[0]),
        'stats': {k: v for k, v in stats.items() if k != 'segments'},
        'route': [
            {
                'order': i+1,
                'name': s.name,
                'city': s.city,
                'state': s.state,
                'lat': s.lat,
                'lon': s.lon,
                'visit_duration_hours': s.visit_duration_hours
            }
            for i, s in enumerate(optimized_route)
        ],
        'segments': stats['segments']
    }

    with open('optimized_10_site_route.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(f"\n{'='*70}")
    print(f"✓ Route saved to optimized_10_site_route.json")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
