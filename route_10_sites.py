#!/usr/bin/env python3
"""
Route 10 NPS Sites using OR-Tools
Pulls data from Chroma vector database
"""

import json
import math
from typing import List, Tuple
from dataclasses import dataclass
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
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


def create_distance_matrix(locations: List[Tuple[float, float]]) -> List[List[int]]:
    """Build distance matrix in meters"""
    n = len(locations)
    matrix = [[0] * n for _ in range(n)]

    for i in range(n):
        for j in range(n):
            if i != j:
                miles = haversine_distance(
                    locations[i][0], locations[i][1],
                    locations[j][0], locations[j][1]
                )
                meters = int(miles * 1609.34)
                matrix[i][j] = meters

    return matrix


def solve_tsp_ortools(distance_matrix: List[List[int]], start_index: int = 0) -> List[int]:
    """Solve TSP using OR-Tools"""
    manager = pywrapcp.RoutingIndexManager(len(distance_matrix), 1, start_index)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distance_matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.seconds = 30

    solution = routing.SolveWithParameters(search_parameters)

    if solution:
        route = []
        index = routing.Start(0)
        while not routing.IsEnd(index):
            route.append(manager.IndexToNode(index))
            index = solution.Value(routing.NextVar(index))
        route.append(manager.IndexToNode(index))
        return route

    return None


def calculate_trip_stats(route: List[Site], start_loc: Tuple[float, float]) -> dict:
    """Calculate comprehensive trip statistics"""
    total_distance = 0
    current_lat, current_lon = start_loc

    for site in route:
        dist = haversine_distance(current_lat, current_lon, site.lat, site.lon)
        total_distance += dist
        current_lat, current_lon = site.lat, site.lon

    # Return to start
    return_dist = haversine_distance(current_lat, current_lon, start_loc[0], start_loc[1])
    total_distance += return_dist

    total_drive_hours = total_distance / 55.0  # 55 mph average
    total_visit_hours = sum(s.visit_duration_hours for s in route)

    return {
        'total_distance_miles': round(total_distance, 1),
        'total_drive_hours': round(total_drive_hours, 1),
        'total_visit_hours': round(total_visit_hours, 1),
        'total_trip_hours': round(total_drive_hours + total_visit_hours, 1),
        'site_count': len(route)
    }


async def main():
    print("="*70)
    print("Route 10 NPS Sites - Minimum Travel Time")
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

    # Build distance matrix
    locations = [(s.lat, s.lon) for s in sites]
    print("\nBuilding distance matrix...")
    dist_matrix = create_distance_matrix(locations)

    # Solve TSP
    print("Solving TSP for optimal route...")
    route_indices = solve_tsp_ortools(dist_matrix, start_index=0)

    if route_indices:
        # Extract optimized route
        optimized_route = [sites[i] for i in route_indices]

        # Calculate stats
        stats = calculate_trip_stats(optimized_route, start_loc)

        print(f"\n{'='*70}")
        print("OPTIMIZED ROUTE")
        print(f"{'='*70}")
        print(f"\nStats:")
        print(f"  Sites: {stats['site_count']}")
        print(f"  Total distance: {stats['total_distance_miles']} miles")
        print(f"  Driving time: {stats['total_drive_hours']} hours")
        print(f"  Visit time: {stats['total_visit_hours']} hours")
        print(f"  Total trip time: {stats['total_trip_hours']} hours")
        print(f"  Estimated days: {max(1, int(stats['total_trip_hours'] / 12))}")

        print(f"\nRoute:")
        for i, site in enumerate(optimized_route, 1):
            print(f"  {i}. {site}")

        # Save to JSON
        result = {
            'start_location': f"{sites[0].name}, {sites[0].city}, {sites[0].state}",
            'stats': stats,
            'route': [
                {
                    'name': s.name,
                    'city': s.city,
                    'state': s.state,
                    'lat': s.lat,
                    'lon': s.lon
                }
                for s in optimized_route
            ]
        }

        with open('optimized_10_site_route.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)

        print(f"\nSaved route to optimized_10_site_route.json")
        print(f"{'='*70}")
    else:
        print("Error: Could not find optimal route")


if __name__ == '__main__':
    asyncio.run(main())
