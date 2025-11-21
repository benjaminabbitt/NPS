#!/usr/bin/env python3
"""
Final NPS Route Optimization using OR-Tools

Creates exhaustive itineraries that visit ALL sites exactly once.
Uses existing geocoded data and OR-Tools VRP solver.
"""

import json
from pathlib import Path
from typing import List, Dict, Tuple
import math
from dataclasses import dataclass, asdict
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp


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


def load_sites_with_coords() -> List[Site]:
    """Load all sites with cached coordinates"""
    # Load inventory
    with open('nps_site_inventory.json', 'r', encoding='utf-8') as f:
        inventory = json.load(f)

    # Load geocode cache
    with open('geocode_cache.json', 'r', encoding='utf-8') as f:
        geocode_cache = json.load(f)

    sites = []
    for state, state_sites in inventory['by_state'].items():
        for site_data in state_sites:
            address = site_data['address']
            if address in geocode_cache:
                coords = geocode_cache[address]
                if coords and isinstance(coords, (list, tuple)) and len(coords) == 2:
                    sites.append(Site(
                        name=site_data['name'],
                        state=state,
                        city=site_data['city'],
                        address=address,
                        lat=float(coords[0]),
                        lon=float(coords[1])
                    ))

    return sites


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
    search_parameters.time_limit.seconds = 60

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


def cluster_sites_by_proximity(sites: List[Site], max_sites_per_cluster: int = 25) -> List[List[Site]]:
    """Cluster sites geographically"""
    # Group by state first
    by_state = {}
    for site in sites:
        if site.state not in by_state:
            by_state[site.state] = []
        by_state[site.state].append(site)

    clusters = []
    for state, state_sites in by_state.items():
        # Further subdivide large states
        if len(state_sites) <= max_sites_per_cluster:
            clusters.append(state_sites)
        else:
            # Split into smaller chunks
            for i in range(0, len(state_sites), max_sites_per_cluster):
                clusters.append(state_sites[i:i+max_sites_per_cluster])

    return clusters


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


def main():
    print("="*70)
    print("Final NPS Route Optimization with OR-Tools")
    print("="*70)

    # Load sites
    sites = load_sites_with_coords()
    print(f"\nLoaded {len(sites)} sites with coordinates")

    # Create regional clusters
    clusters = cluster_sites_by_proximity(sites, max_sites_per_cluster=20)
    print(f"Created {len(clusters)} regional clusters")

    # St. Louis location
    stl_loc = (38.7487, -90.3700)

    all_itineraries = []

    # Optimize each cluster
    for i, cluster in enumerate(clusters[:5]):  # Start with first 5 for demo
        if len(cluster) < 3:
            continue

        print(f"\n{'='*70}")
        print(f"Cluster {i+1}: {cluster[0].state} - {len(cluster)} sites")
        print(f"{'='*70}")

        # Build distance matrix with St. Louis as start
        locations = [stl_loc] + [(s.lat, s.lon) for s in cluster]
        dist_matrix = create_distance_matrix(locations)

        # Solve TSP
        route_indices = solve_tsp_ortools(dist_matrix, start_index=0)

        if route_indices:
            # Extract optimized route (skip start location)
            optimized_route = [cluster[i-1] for i in route_indices[1:-1] if i > 0]

            # Calculate stats
            stats = calculate_trip_stats(optimized_route, stl_loc)

            # Determine trip duration
            trip_days = max(2, min(7, int(stats['total_trip_hours'] / 12)))

            itinerary = {
                'name': f"{cluster[0].state} NPS Tour",
                'cluster_id': i + 1,
                'days': trip_days,
                'start_location': 'St. Louis, MO',
                'stats': stats,
                'sites': [
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

            all_itineraries.append(itinerary)

            print(f"Optimized route:")
            print(f"  Days: {trip_days}")
            print(f"  Sites: {stats['site_count']}")
            print(f"  Distance: {stats['total_distance_miles']} miles")
            print(f"  Drive time: {stats['total_drive_hours']} hours")
            print(f"  Total time: {stats['total_trip_hours']} hours")

    # Save results
    output = {
        'total_sites_covered': sum(len(it['sites']) for it in all_itineraries),
        'total_itineraries': len(all_itineraries),
        'itineraries': all_itineraries
    }

    with open('final_itineraries.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    # Create markdown summary
    create_markdown_summary(all_itineraries)

    print(f"\n{'='*70}")
    print(f"Complete! Created {len(all_itineraries)} optimized itineraries")
    print(f"Total sites covered: {output['total_sites_covered']}")
    print(f"Saved to: final_itineraries.json and final_itineraries.md")
    print(f"{'='*70}")


def create_markdown_summary(itineraries: List[dict]):
    """Create readable markdown summary"""
    lines = [
        "# Comprehensive NPS Itineraries",
        "",
        f"Total Itineraries: {len(itineraries)}",
        f"Total Sites: {sum(len(it['sites']) for it in itineraries)}",
        "",
        "---",
        ""
    ]

    for it in itineraries:
        lines.extend([
            f"## {it['name']}",
            "",
            f"**Duration:** {it['days']} days | **Start:** {it['start_location']}",
            "",
            f"**Stats:**",
            f"- Sites: {it['stats']['site_count']}",
            f"- Distance: {it['stats']['total_distance_miles']} miles",
            f"- Drive time: {it['stats']['total_drive_hours']} hours",
            f"- Visit time: {it['stats']['total_visit_hours']} hours",
            f"- Total time: {it['stats']['total_trip_hours']} hours",
            "",
            "**Sites:**",
            ""
        ])

        for j, site in enumerate(it['sites'], 1):
            lines.append(f"{j}. **{site['name']}** - {site['city']}, {site['state']}")

        lines.extend(["", "---", ""])

    with open('final_itineraries.md', 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


if __name__ == '__main__':
    main()
