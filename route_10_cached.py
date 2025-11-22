#!/usr/bin/env python3
"""
Route 10 NPS Sites using cached geocodes
"""

import json
import math
import re
from typing import List, Tuple
from dataclasses import dataclass
import chromadb


@dataclass
class Site:
    """NPS Site with location"""
    name: str
    state: str
    city: str
    address: str
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


def extract_first_address(document: str) -> Tuple[str, str, str]:
    """Extract first address from cancellation stamps section"""
    lines = document.split('\n')

    for line in lines:
        # Look for pattern: (address; hours; phone)
        match = re.search(r'\(([^;]+),\s*([A-Z]{2})\s+(\d{5})', line)
        if match:
            full_address = match.group(0)[1:]  # Remove leading (
            # Get just the address part (before first semicolon)
            address_part = full_address.split(';')[0].strip()

            # Extract city and state
            parts = address_part.split(',')
            if len(parts) >= 3:
                city = parts[-2].strip()
                state = match.group(2)
                return address_part, city, state

    return None, None, None


def load_sites_from_chroma(limit: int = 10) -> List[Site]:
    """Load sites from Chroma database with cached geocodes"""
    print("Loading sites from Chroma database...")

    # Load geocode cache
    try:
        with open('geocode_cache.json', 'r') as f:
            geocode_cache = json.load(f)
    except FileNotFoundError:
        print("Error: geocode_cache.json not found!")
        return []

    # Connect to Chroma
    client = chromadb.PersistentClient(path="./chroma.db")
    collection = client.get_collection(name="nps_research")

    # Get documents
    results = collection.get(
        limit=limit,
        include=["documents", "metadatas"]
    )

    sites = []

    for doc, metadata in zip(results['documents'], results['metadatas']):
        site_name = metadata.get('site_name', 'Unknown Site')

        # Extract address
        address, city, state = extract_first_address(doc)

        if address:
            # Try to find in cache (try exact match and variations)
            coords = None

            # Try exact match first
            if address in geocode_cache:
                coords = geocode_cache[address]
            else:
                # Try to find by fuzzy matching (check if address is a key subset)
                for cached_addr, cached_coords in geocode_cache.items():
                    if address.lower() in cached_addr.lower() or cached_addr.lower() in address.lower():
                        coords = cached_coords
                        break

            if coords and isinstance(coords, (list, tuple)) and len(coords) == 2:
                sites.append(Site(
                    name=site_name,
                    state=state or "Unknown",
                    city=city or "Unknown",
                    address=address,
                    lat=float(coords[0]),
                    lon=float(coords[1])
                ))
                print(f"  ✓ {site_name}: {city}, {state}")
            else:
                print(f"  ✗ {site_name}: No coordinates in cache")
        else:
            print(f"  ✗ {site_name}: No address found")

    return sites


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
    print("Route 10 NPS Sites - Using Cached Geocodes")
    print("="*70)

    # Load sites
    sites = load_sites_from_chroma(limit=10)
    print(f"\nSuccessfully loaded {len(sites)} sites with coordinates\n")

    if len(sites) < 2:
        print("Error: Not enough sites geocoded. Need at least 2 sites.")
        return

    # Use first site as starting point
    start_loc = (sites[0].lat, sites[0].lon)
    print(f"Start location: {sites[0]}\n")

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
    print(f"  Estimated days: {max(1, int(stats['total_trip_hours'] / 12))}")

    print(f"\nRoute Itinerary:")
    for i, site in enumerate(optimized_route, 1):
        print(f"  {i}. {site}")

    print(f"\nDriving Segments:")
    for seg in stats['segments']:
        print(f"  {seg['from']} → {seg['to']}")
        print(f"    {seg['distance_miles']} mi, ~{seg['drive_hours']} hrs")

    # Save to JSON
    result = {
        'algorithm': 'nearest_neighbor',
        'start_location': str(sites[0]),
        'stats': {k: v for k, v in stats.items() if k != 'segments'},
        'route': [
            {
                'order': i+1,
                'name': s.name,
                'city': s.city,
                'state': s.state,
                'address': s.address,
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
