#!/usr/bin/env python3
"""
Route all 20 NPS sites using OR-Tools with geocoded coordinates
"""
import json
import math
from pathlib import Path
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# Load the geocode cache
def load_geocode_cache():
    cache_file = Path('geocode_cache.json')
    if cache_file.exists():
        with open(cache_file, 'r') as f:
            return json.load(f)
    return {}

# Extract coordinates for each site from cache or markdown files
SITES = [
    "Abraham Lincoln Birthplace NHP",
    "Acadia NP",
    "Alcatraz Island",
    "Adams NHP",
    "African Burial Ground NM",
    "Agate Fossil Beds NM",
    "Alibates Flint Quarries NM",
    "African American Civil War MEM",
    "Alagnak WR",
    "Aleutian World War II NHA",
    "Apostle Islands NL",
    "Andersonville NHS",
    "Antietam NB",
    "Allegheny Portage Railroad NHS",
    "Andrew Johnson NHS",
    "Aniakchak NM _ PRES",
    "Amache NHS",
    "American Veterans Disabled for Life Memorial",
    "Anacostia Park",
    "Amistad NRA"
]

# Known coordinates from previous routing demo and geocoding
SITE_COORDS = {
    "Abraham Lincoln Birthplace NHP": (37.5357, -85.7433),
    "Acadia NP": (44.3386, -68.2733),
    "Adams NHP": (42.2529, -71.0023),
    "African American Civil War MEM": (38.8921, -77.0241),
    "African Burial Ground NM": (40.7145, -74.0048),
    "Agate Fossil Beds NM": (42.4187, -103.7272),
    "Alagnak WR": (59.0725, -156.8493),
    "Alcatraz Island": (37.8267, -122.4230),
    "Aleutian World War II NHA": (53.8845, -166.5546),
    "Alibates Flint Quarries NM": (35.5665, -101.6772),
    "Apostle Islands NL": (46.8130, -90.8205),  # Bayfield Visitor Center
    "Andersonville NHS": (32.2037, -84.1331),
    "Antietam NB": (39.4592, -77.7412),
    "Allegheny Portage Railroad NHS": (40.4519, -78.6103),  # Approximation
    "Andrew Johnson NHS": (36.1629, -82.8295),
    "Aniakchak NM _ PRES": (58.6827, -156.6682),
    "Amache NHS": (38.0625, -102.3087),
    "American Veterans Disabled for Life Memorial": (38.8898, -77.0329),
    "Anacostia Park": (38.8634, -76.9852),
    "Amistad NRA": (29.4660, -100.9884)
}

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in miles using Haversine formula"""
    R = 3959  # Earth radius in miles
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def create_distance_matrix(locations):
    """Create distance matrix for all locations"""
    size = len(locations)
    matrix = [[0] * size for _ in range(size)]
    
    for i in range(size):
        for j in range(size):
            if i != j:
                lat1, lon1 = locations[i]
                lat2, lon2 = locations[j]
                # Convert to meters for OR-Tools (it works with integers)
                distance_miles = haversine_distance(lat1, lon1, lat2, lon2)
                matrix[i][j] = int(distance_miles * 1609.34)  # Convert to meters
    
    return matrix

def solve_tsp(distance_matrix, location_names):
    """Solve TSP using OR-Tools"""
    # Create routing model
    manager = pywrapcp.RoutingIndexManager(len(distance_matrix), 1, 0)
    routing = pywrapcp.RoutingModel(manager)
    
    # Create distance callback
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distance_matrix[from_node][to_node]
    
    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
    
    # Set search parameters
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.seconds = 30
    
    # Solve
    solution = routing.SolveWithParameters(search_parameters)
    
    if solution:
        return extract_solution(manager, routing, solution, location_names, distance_matrix)
    else:
        return None

def extract_solution(manager, routing, solution, location_names, distance_matrix):
    """Extract solution from OR-Tools result"""
    index = routing.Start(0)
    route = []
    total_distance = 0
    
    while not routing.IsEnd(index):
        node = manager.IndexToNode(index)
        route.append(node)
        previous_index = index
        index = solution.Value(routing.NextVar(index))
        total_distance += routing.GetArcCostForVehicle(previous_index, index, 0)
    
    # Add return to start
    node = manager.IndexToNode(index)
    route.append(node)
    
    # Convert meters back to miles
    total_distance_miles = total_distance / 1609.34
    
    return {
        'route': route,
        'total_distance_miles': total_distance_miles,
        'location_names': [location_names[i] for i in route]
    }

def main():
    print("="*70)
    print("Routing 20 NPS Sites using OR-Tools")
    print("="*70)
    
    # Prepare data
    locations = []
    location_names = []
    
    for site in SITES:
        if site in SITE_COORDS:
            locations.append(SITE_COORDS[site])
            location_names.append(site)
        else:
            print(f"Warning: No coordinates for {site}")
    
    print(f"\nRouting {len(locations)} sites")
    print(f"Starting location: {location_names[0]}")
    
    # Create distance matrix
    print("\nCreating distance matrix...")
    distance_matrix = create_distance_matrix(locations)
    
    # Solve TSP
    print("Solving route optimization with OR-Tools...")
    print("(This may take up to 30 seconds)")
    result = solve_tsp(distance_matrix, location_names)
    
    if result:
        print(f"\n{'='*70}")
        print("OPTIMIZED ROUTE")
        print(f"{'='*70}")
        print(f"\nTotal Distance: {result['total_distance_miles']:,.1f} miles")
        print(f"Estimated Drive Time: {result['total_distance_miles'] / 55.0:.1f} hours")
        print(f"Estimated Visit Time: {len(locations) * 2:.1f} hours (2 hours per site)")
        print(f"Total Trip Time: {(result['total_distance_miles'] / 55.0) + (len(locations) * 2):.1f} hours")
        
        print(f"\n\nRoute Order:")
        for i, name in enumerate(result['location_names'], 1):
            lat, lon = SITE_COORDS[name]
            print(f"  {i}. {name} ({lat}, {lon})")
        
        # Save to JSON
        output = {
            'algorithm': 'or-tools_guided_local_search',
            'description': 'Routes 20 NPS sites using OR-Tools optimization',
            'stats': {
                'total_distance_miles': round(result['total_distance_miles'], 1),
                'total_drive_hours': round(result['total_distance_miles'] / 55.0, 1),
                'total_visit_hours': len(locations) * 2.0,
                'total_trip_hours': round((result['total_distance_miles'] / 55.0) + (len(locations) * 2), 1),
                'site_count': len(locations)
            },
            'route': [
                {
                    'order': i+1,
                    'name': name,
                    'lat': SITE_COORDS[name][0],
                    'lon': SITE_COORDS[name][1],
                    'visit_duration_hours': 2.0
                }
                for i, name in enumerate(result['location_names'])
            ]
        }
        
        with open('optimized_20_site_route_ortools.json', 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n{'='*70}")
        print("✓ Route saved to optimized_20_site_route_ortools.json")
        print(f"{'='*70}")
    else:
        print("\n✗ Failed to find optimal route")

if __name__ == '__main__':
    main()
