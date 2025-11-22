#!/usr/bin/env python3
"""
Route 10 NPS Sites using Nearest Neighbor Heuristic
Pulls data from Chroma vector database - no external dependencies
"""

import json
import math
from typing import List, Tuple
from dataclasses import dataclass
import chromadb
import asyncio
import httpx
import urllib.parse


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


async def geocode_address(address: str) -> Tuple[float, float]:
    """Geocode a single address using Nominatim"""
    try:
        async with httpx.AsyncClient() as client:
            url = f"https://nominatim.openstreetmap.org/search?{urllib.parse.urlencode({'q': address, 'format': 'json', 'limit': 1})}"
            headers = {'User-Agent': 'NPS-Router/1.0'}

            response = await client.get(url, headers=headers, timeout=10.0)
            data = response.json()

            if data:
                return (float(data[0]['lat']), float(data[0]['lon']))

    except Exception as e:
        print(f"Geocoding error for {address}: {e}")

    return None


async def load_sites_from_chroma(limit: int = 10) -> List[Site]:
    """Load sites from Chroma database"""
    print("Loading sites from Chroma database...")

    # Connect to Chroma
    client = chromadb.PersistentClient(path="./chroma.db")
    collection = client.get_collection(name="nps_research")

    # Get all documents
    results = collection.get(
        limit=limit,
        include=["documents", "metadatas"]
    )

    sites = []

    for i, (doc, metadata) in enumerate(zip(results['documents'], results['metadatas'])):
        site_name = metadata.get('site_name', f'Site {i+1}')

        # Extract location from document
        # Look for address in cancellation stamps section
        address = None
        city = None
        state = None

        lines = doc.split('\n')
        for j, line in enumerate(lines):
            # Find first address in cancellation stamps
            if '(' in line and ')' in line and any(st in line for st in ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC']):
                # Extract address from parentheses
                start = line.find('(')
                end = line.find(';', start)
                if end == -1:
                    end = line.find(')', start)

                if start != -1 and end != -1:
                    address = line[start+1:end].strip()

                    # Extract city and state
                    parts = address.split(',')
                    if len(parts) >= 2:
                        city = parts[-2].strip()
                        state_zip = parts[-1].strip().split()
                        if state_zip:
                            state = state_zip[0]

                    break

        if address:
            print(f"  {site_name}: {address}")
            # Geocode the address
            coords = await geocode_address(address)

            if coords:
                await asyncio.sleep(1.1)  # Rate limiting
                sites.append(Site(
                    name=site_name,
                    state=state or "Unknown",
                    city=city or "Unknown",
                    lat=coords[0],
                    lon=coords[1]
                ))

                if len(sites) >= limit:
                    break

    return sites


def nearest_neighbor_route(sites: List[Site], start_index: int = 0) -> List[Site]:
    """
    Simple nearest neighbor heuristic for TSP
    Not optimal but fast and reasonable for small problems
    """
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

    for site in route:
        dist = haversine_distance(current_lat, current_lon, site.lat, site.lon)
        total_distance += dist
        segments.append({
            'to': str(site),
            'distance_miles': round(dist, 1),
            'drive_hours': round(dist / 55.0, 1)
        })
        current_lat, current_lon = site.lat, site.lon

    # Return to start
    return_dist = haversine_distance(current_lat, current_lon, start_loc[0], start_loc[1])
    total_distance += return_dist
    segments.append({
        'to': 'Return to start',
        'distance_miles': round(return_dist, 1),
        'drive_hours': round(return_dist / 55.0, 1)
    })

    total_drive_hours = total_distance / 55.0  # 55 mph average
    total_visit_hours = sum(s.visit_duration_hours for s in route)

    return {
        'total_distance_miles': round(total_distance, 1),
        'total_drive_hours': round(total_drive_hours, 1),
        'total_visit_hours': round(total_visit_hours, 1),
        'total_trip_hours': round(total_drive_hours + total_visit_hours, 1),
        'site_count': len(route),
        'segments': segments
    }


async def main():
    print("="*70)
    print("Route 10 NPS Sites - Nearest Neighbor Algorithm")
    print("="*70)

    # Load sites from Chroma
    sites = await load_sites_from_chroma(limit=10)
    print(f"\nSuccessfully loaded {len(sites)} sites with coordinates")

    if len(sites) < 2:
        print("Error: Not enough sites geocoded. Need at least 2 sites.")
        return

    # Use first site as starting point
    start_loc = (sites[0].lat, sites[0].lon)
    print(f"\nStart location: {sites[0]}")

    # Solve using nearest neighbor
    print("\nFinding route using nearest neighbor algorithm...")
    optimized_route = nearest_neighbor_route(sites, start_index=0)

    # Calculate stats
    stats = calculate_trip_stats(optimized_route, start_loc)

    print(f"\n{'='*70}")
    print("OPTIMIZED ROUTE")
    print(f"{'='*70}")
    print(f"\nTrip Stats:")
    print(f"  Sites visited: {stats['site_count']}")
    print(f"  Total distance: {stats['total_distance_miles']} miles")
    print(f"  Total driving time: {stats['total_drive_hours']} hours")
    print(f"  Total visit time: {stats['total_visit_hours']} hours")
    print(f"  Total trip time: {stats['total_trip_hours']} hours")
    print(f"  Estimated days: {max(1, int(stats['total_trip_hours'] / 12))}")

    print(f"\nRoute with segments:")
    for i, (site, segment) in enumerate(zip(optimized_route, stats['segments']), 1):
        print(f"  {i}. {site}")
        print(f"     -> Drive to next: {segment['distance_miles']} mi, {segment['drive_hours']} hrs")

    # Save to JSON
    result = {
        'algorithm': 'nearest_neighbor',
        'start_location': f"{sites[0].name}, {sites[0].city}, {sites[0].state}",
        'stats': stats,
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
        ]
    }

    with open('optimized_10_site_route.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(f"\n{'='*70}")
    print(f"Route saved to optimized_10_site_route.json")
    print(f"{'='*70}")


if __name__ == '__main__':
    asyncio.run(main())
