#!/usr/bin/env python3
"""
NPS Site Route Optimization and Itinerary Builder

This script parses NPS site data from CSV files and creates optimized
road trip itineraries based on geographic clustering and route optimization.
"""

import csv
import json
import math
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import urllib.request
import urllib.parse
import time

class NPSSite:
    """Represents a National Park Service site"""
    def __init__(self, data: dict):
        self.state = data.get('State', '').strip()
        self.name = data.get('National Park', '').strip()
        self.address = data.get('Address', '').strip()
        self.city = data.get('City', '').strip()
        self.zip_code = data.get('Zip', '').strip()
        self.in_book = data.get('In the Book', '').strip()
        self.completed = data.get('Completed', '').strip()
        self.est_hours = data.get('Est. Hours', '').strip()

        # Parse hours for each day
        self.hours = {
            'Sunday': data.get('Sunday', '').strip(),
            'Monday': data.get('Monday', '').strip(),
            'Tuesday': data.get('Tuesday', '').strip(),
            'Wednesday': data.get('Wednesday', '').strip(),
            'Thursday': data.get('Thursday', '').strip(),
            'Friday': data.get('Friday', '').strip(),
            'Saturday': data.get('Saturday', '').strip(),
        }

        # Visitor center info
        self.vc_location = data.get('Visitor Center Location', '').strip()
        self.vc_address = data.get('Visitor Center Address', '').strip()
        self.vc_city = data.get('Visitor Center City', '').strip()
        self.vc_state = data.get('Visitor Center State', '').strip()

        # Geocoding placeholders
        self.lat = None
        self.lon = None

    def __repr__(self):
        return f"NPSSite({self.name}, {self.city}, {self.state})"

    def full_address(self) -> str:
        """Return formatted full address for geocoding"""
        parts = [self.address, self.city, self.state, self.zip_code]
        return ', '.join([p for p in parts if p])

    def is_open_on_day(self, day: str) -> bool:
        """Check if site is open on a given day"""
        hours = self.hours.get(day, '')
        return hours and hours.lower() not in ['closed', '']

    def get_hours_for_day(self, day: str) -> str:
        """Get operating hours for a specific day"""
        return self.hours.get(day, 'Unknown')


class RouteOptimizer:
    """Optimizes routes between NPS sites"""

    # Major airports for route planning
    MAJOR_AIRPORTS = {
        'ATL': {'name': 'Atlanta', 'lat': 33.6407, 'lon': -84.4277, 'city': 'Atlanta, GA'},
        'BHM': {'name': 'Birmingham', 'lat': 33.5627, 'lon': -86.7537, 'city': 'Birmingham, AL'},
        'STL': {'name': 'St. Louis', 'lat': 38.7487, 'lon': -90.3700, 'city': 'St. Louis, MO'},
        'DEN': {'name': 'Denver', 'lat': 39.8561, 'lon': -104.6737, 'city': 'Denver, CO'},
        'LAX': {'name': 'Los Angeles', 'lat': 33.9416, 'lon': -118.4085, 'city': 'Los Angeles, CA'},
        'SEA': {'name': 'Seattle', 'lat': 47.4502, 'lon': -122.3088, 'city': 'Seattle, WA'},
        'PHX': {'name': 'Phoenix', 'lat': 33.4352, 'lon': -112.0101, 'city': 'Phoenix, AZ'},
        'ANC': {'name': 'Anchorage', 'lat': 61.1743, 'lon': -149.9963, 'city': 'Anchorage, AK'},
    }

    def __init__(self):
        self.sites: List[NPSSite] = []
        self.geocode_cache: Dict[str, Tuple[float, float]] = {}

    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula (in miles)"""
        R = 3959  # Earth's radius in miles

        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        return R * c

    def estimate_drive_time(self, distance_miles: float) -> float:
        """Estimate driving time in hours (assumes average 55 mph)"""
        return distance_miles / 55.0

    def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """Geocode an address using Nominatim (OpenStreetMap)"""
        if address in self.geocode_cache:
            return self.geocode_cache[address]

        try:
            # Use Nominatim API (free, no API key required)
            base_url = 'https://nominatim.openstreetmap.org/search'
            params = {
                'q': address,
                'format': 'json',
                'limit': 1
            }

            url = f"{base_url}?{urllib.parse.urlencode(params)}"
            headers = {'User-Agent': 'NPS-Route-Planner/1.0'}

            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())

            if data and len(data) > 0:
                lat = float(data[0]['lat'])
                lon = float(data[0]['lon'])
                self.geocode_cache[address] = (lat, lon)
                time.sleep(1.1)  # Rate limiting: max 1 request per second
                return (lat, lon)

        except Exception as e:
            print(f"Geocoding error for {address}: {e}")

        return None

    def load_sites_from_csv(self, csv_path: str) -> None:
        """Load sites from CSV file"""
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Skip empty rows
                if not row.get('National Park', '').strip():
                    continue

                site = NPSSite(row)
                self.sites.append(site)

        print(f"Loaded {len(self.sites)} sites from {csv_path}")

    def geocode_all_sites(self) -> None:
        """Geocode all loaded sites"""
        print(f"Geocoding {len(self.sites)} sites...")

        for i, site in enumerate(self.sites):
            if i % 10 == 0:
                print(f"  Progress: {i}/{len(self.sites)}")

            coords = self.geocode_address(site.full_address())
            if coords:
                site.lat, site.lon = coords

        geocoded_count = sum(1 for s in self.sites if s.lat is not None)
        print(f"Successfully geocoded {geocoded_count}/{len(self.sites)} sites")

    def find_sites_by_state(self, state: str) -> List[NPSSite]:
        """Find all sites in a given state"""
        return [s for s in self.sites if s.state.upper() == state.upper()]

    def find_nearest_airport(self, site: NPSSite) -> Tuple[str, dict]:
        """Find the nearest major airport to a site"""
        if not site.lat or not site.lon:
            return None, None

        nearest = None
        min_distance = float('inf')

        for code, airport in self.MAJOR_AIRPORTS.items():
            distance = self.haversine_distance(
                site.lat, site.lon,
                airport['lat'], airport['lon']
            )
            if distance < min_distance:
                min_distance = distance
                nearest = (code, airport)

        return nearest

    def cluster_sites_by_region(self, max_distance: float = 200) -> Dict[str, List[NPSSite]]:
        """Cluster sites into regional groups based on proximity"""
        clusters = defaultdict(list)

        # Group by state first, then by proximity within state
        by_state = defaultdict(list)
        for site in self.sites:
            if site.lat and site.lon:
                by_state[site.state].append(site)

        # Further cluster within each state
        cluster_id = 0
        for state, state_sites in by_state.items():
            if not state_sites:
                continue

            visited = set()
            for site in state_sites:
                if site in visited:
                    continue

                cluster_name = f"{state}_{cluster_id}"
                cluster = [site]
                visited.add(site)

                # Find nearby sites
                for other in state_sites:
                    if other in visited:
                        continue

                    distance = self.haversine_distance(
                        site.lat, site.lon,
                        other.lat, other.lon
                    )

                    if distance <= max_distance:
                        cluster.append(other)
                        visited.add(other)

                clusters[cluster_name] = cluster
                cluster_id += 1

        return dict(clusters)

    def nearest_neighbor_route(self, sites: List[NPSSite], start_lat: float, start_lon: float) -> List[NPSSite]:
        """Create a route using nearest neighbor algorithm"""
        if not sites:
            return []

        unvisited = sites.copy()
        route = []
        current_lat, current_lon = start_lat, start_lon

        while unvisited:
            # Find nearest unvisited site
            nearest = min(
                unvisited,
                key=lambda s: self.haversine_distance(current_lat, current_lon, s.lat, s.lon) if s.lat and s.lon else float('inf')
            )

            if not nearest.lat or not nearest.lon:
                unvisited.remove(nearest)
                continue

            route.append(nearest)
            unvisited.remove(nearest)
            current_lat, current_lon = nearest.lat, nearest.lon

        return route

    def create_itinerary(self, sites: List[NPSSite], start_location: str, days: int) -> dict:
        """Create a multi-day itinerary"""
        if not sites:
            return {'error': 'No sites provided'}

        # Calculate total distance and time
        total_distance = 0
        total_drive_time = 0

        # Estimate sites per day
        sites_per_day = max(1, len(sites) // days)

        itinerary = {
            'start_location': start_location,
            'total_days': days,
            'total_sites': len(sites),
            'daily_plans': []
        }

        for day in range(days):
            start_idx = day * sites_per_day
            end_idx = start_idx + sites_per_day if day < days - 1 else len(sites)
            day_sites = sites[start_idx:end_idx]

            day_plan = {
                'day': day + 1,
                'sites': [
                    {
                        'name': s.name,
                        'city': s.city,
                        'state': s.state,
                        'address': s.full_address(),
                        'hours': s.hours
                    }
                    for s in day_sites
                ]
            }

            itinerary['daily_plans'].append(day_plan)

        return itinerary


def main():
    """Main execution function"""
    print("NPS Route Optimizer and Itinerary Builder")
    print("=" * 50)

    optimizer = RouteOptimizer()

    # Load sites from CSV
    csv_path = r"C:\Users\Ben\workspace\NPS\Cancellation Stamp Sites with Timing\Inputs\Untitled spreadsheet - US Parks.csv"
    optimizer.load_sites_from_csv(csv_path)

    # Get summary by state
    by_state = defaultdict(list)
    for site in optimizer.sites:
        by_state[site.state].append(site)

    print("\nSites by State:")
    for state in sorted(by_state.keys()):
        if state:
            print(f"  {state}: {len(by_state[state])} sites")

    # Save site inventory
    with open('nps_site_inventory.json', 'w', encoding='utf-8') as f:
        inventory = {
            'total_sites': len(optimizer.sites),
            'by_state': {
                state: [
                    {
                        'name': s.name,
                        'city': s.city,
                        'address': s.full_address(),
                        'hours': s.hours
                    }
                    for s in sites
                ]
                for state, sites in by_state.items() if state
            }
        }
        json.dump(inventory, f, indent=2)

    print("\nSaved site inventory to nps_site_inventory.json")

    return optimizer


if __name__ == '__main__':
    optimizer = main()
