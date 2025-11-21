#!/usr/bin/env python3
"""
Advanced NPS Itinerary Builder

Creates optimized 2-3 day and week-long road trip itineraries
with geocoding, route optimization, and schedule generation.
"""

import csv
import json
import math
import urllib.request
import urllib.parse
import time
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple, Optional


class Site:
    def __init__(self, data: dict):
        self.name = data.get('name', '')
        self.city = data.get('city', '')
        self.state = data.get('state', '')
        self.address = data.get('address', '')
        self.hours = data.get('hours', {})
        self.lat = data.get('lat')
        self.lon = data.get('lon')
        self.est_visit_hours = 2.0  # Default estimate

    def is_open(self, day_name: str) -> bool:
        hours = self.hours.get(day_name, '').strip()
        return hours and hours.lower() not in ['closed', '']

    def __repr__(self):
        return f"{self.name} ({self.city}, {self.state})"


class ItineraryBuilder:
    AIRPORTS = {
        'ATL': {'name': 'Atlanta', 'lat': 33.6407, 'lon': -84.4277, 'states': ['GA', 'AL', 'SC', 'NC', 'TN']},
        'BHM': {'name': 'Birmingham', 'lat': 33.5627, 'lon': -86.7537, 'states': ['AL', 'MS']},
        'STL': {'name': 'St. Louis', 'lat': 38.7487, 'lon': -90.3700, 'states': ['MO', 'IL', 'KY', 'TN', 'AR']},
        'DEN': {'name': 'Denver', 'lat': 39.8561, 'lon': -104.6737, 'states': ['CO', 'WY', 'NE', 'KS']},
        'LAX': {'name': 'Los Angeles', 'lat': 33.9416, 'lon': -118.4085, 'states': ['CA']},
        'SEA': {'name': 'Seattle', 'lat': 47.4502, 'lon': -122.3088, 'states': ['WA', 'OR']},
        'PHX': {'name': 'Phoenix', 'lat': 33.4352, 'lon': -112.0101, 'states': ['AZ', 'NM']},
        'ANC': {'name': 'Anchorage', 'lat': 61.1743, 'lon': -149.9963, 'states': ['AK']},
        'DCA': {'name': 'Washington DC', 'lat': 38.8521, 'lon': -77.0377, 'states': ['DC', 'VA', 'MD']},
    }

    DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    def __init__(self):
        self.sites: List[Site] = []
        self.geocode_cache: Dict[str, Tuple[float, float]] = {}
        self.load_geocode_cache()

    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in miles"""
        R = 3959
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        return R * 2 * math.asin(math.sqrt(a))

    def geocode(self, address: str) -> Optional[Tuple[float, float]]:
        """Geocode using Nominatim with caching"""
        if address in self.geocode_cache:
            return self.geocode_cache[address]

        try:
            url = f"https://nominatim.openstreetmap.org/search?{urllib.parse.urlencode({'q': address, 'format': 'json', 'limit': 1})}"
            req = urllib.request.Request(url, headers={'User-Agent': 'NPS-Planner/1.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())

            if data:
                coords = (float(data[0]['lat']), float(data[0]['lon']))
                self.geocode_cache[address] = coords
                self.save_geocode_cache()
                time.sleep(1.1)  # Rate limiting
                return coords
        except Exception as e:
            print(f"Geocoding failed for {address}: {e}")

        return None

    def load_geocode_cache(self):
        """Load cached geocodes"""
        try:
            with open('geocode_cache.json', 'r') as f:
                self.geocode_cache = json.load(f)
                print(f"Loaded {len(self.geocode_cache)} cached geocodes")
        except FileNotFoundError:
            print("No geocode cache found, starting fresh")

    def save_geocode_cache(self):
        """Save geocode cache"""
        with open('geocode_cache.json', 'w') as f:
            json.dump(self.geocode_cache, f, indent=2)

    def load_sites(self, inventory_path: str):
        """Load sites from inventory JSON"""
        with open(inventory_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for state, sites in data['by_state'].items():
            for site_data in sites:
                site = Site({
                    'name': site_data['name'],
                    'city': site_data['city'],
                    'state': state,
                    'address': site_data['address'],
                    'hours': site_data['hours']
                })
                self.sites.append(site)

        print(f"Loaded {len(self.sites)} sites")

    def geocode_sites(self, limit: int = 50):
        """Geocode sites (limited to avoid long waits)"""
        print(f"\nGeocoding sites (limit: {limit})...")
        geocoded = 0

        for site in self.sites:
            if site.lat is not None:
                continue

            if geocoded >= limit:
                break

            coords = self.geocode(site.address)
            if coords:
                site.lat, site.lon = coords
                geocoded += 1
                print(f"  [{geocoded}/{limit}] {site.name}")

        print(f"Geocoded {geocoded} new sites")

    def nearest_neighbor_route(self, sites: List[Site], start_lat: float, start_lon: float) -> List[Site]:
        """TSP-like nearest neighbor routing"""
        if not sites:
            return []

        route = []
        remaining = sites.copy()
        current_lat, current_lon = start_lat, start_lon

        while remaining:
            nearest = min(
                remaining,
                key=lambda s: self.haversine_distance(current_lat, current_lon, s.lat, s.lon) if s.lat else float('inf')
            )

            if nearest.lat is None:
                remaining.remove(nearest)
                continue

            route.append(nearest)
            remaining.remove(nearest)
            current_lat, current_lon = nearest.lat, nearest.lon

        return route

    def calculate_route_stats(self, route: List[Site], start_lat: float, start_lon: float) -> dict:
        """Calculate total distance and drive time"""
        total_distance = 0
        current_lat, current_lon = start_lat, start_lon

        for site in route:
            if site.lat and site.lon:
                distance = self.haversine_distance(current_lat, current_lon, site.lat, site.lon)
                total_distance += distance
                current_lat, current_lon = site.lat, site.lon

        # Return to start
        if route and route[0].lat:
            total_distance += self.haversine_distance(current_lat, current_lon, start_lat, start_lon)

        avg_speed = 55  # mph
        total_drive_time = total_distance / avg_speed

        return {
            'total_distance_miles': round(total_distance, 1),
            'total_drive_hours': round(total_drive_time, 1),
            'avg_distance_between_sites': round(total_distance / max(len(route), 1), 1)
        }

    def build_short_trips(self, days: int = 3, sites_per_trip: int = 8):
        """Build 2-3 day airport-based trips"""
        print(f"\n{'='*60}")
        print(f"Building {days}-day airport-based trips")
        print(f"{'='*60}")

        trips = []

        for code, airport in self.AIRPORTS.items():
            # Find sites near this airport
            nearby_sites = []
            for site in self.sites:
                if site.lat and site.lon:
                    distance = self.haversine_distance(
                        airport['lat'], airport['lon'],
                        site.lat, site.lon
                    )
                    if distance <= 300:  # Within 300 miles
                        nearby_sites.append((site, distance))

            if len(nearby_sites) < 3:
                continue

            # Sort by distance and take closest sites
            nearby_sites.sort(key=lambda x: x[1])
            selected_sites = [s[0] for s in nearby_sites[:sites_per_trip]]

            # Optimize route
            route = self.nearest_neighbor_route(selected_sites, airport['lat'], airport['lon'])

            if not route:
                continue

            stats = self.calculate_route_stats(route, airport['lat'], airport['lon'])

            # Split into days
            sites_per_day = max(1, len(route) // days)
            daily_plan = []

            for day in range(days):
                start_idx = day * sites_per_day
                end_idx = start_idx + sites_per_day if day < days - 1 else len(route)
                day_sites = route[start_idx:end_idx]

                daily_plan.append({
                    'day': day + 1,
                    'sites': [str(s) for s in day_sites],
                    'count': len(day_sites)
                })

            trip = {
                'airport': f"{code} - {airport['name']}",
                'days': days,
                'total_sites': len(route),
                'stats': stats,
                'daily_plan': daily_plan,
                'site_details': [
                    {
                        'name': s.name,
                        'city': s.city,
                        'state': s.state,
                        'hours': s.hours
                    }
                    for s in route
                ]
            }

            trips.append(trip)

            print(f"\n{code} ({airport['name']}) - {days} days:")
            print(f"  Sites: {len(route)}")
            print(f"  Distance: {stats['total_distance_miles']} miles")
            print(f"  Drive time: {stats['total_drive_hours']} hours")

        return trips

    def build_stl_week_trip(self):
        """Build week-long trip from St. Louis"""
        print(f"\n{'='*60}")
        print("Building 7-day St. Louis-based trip")
        print(f"{'='*60}")

        stl = self.AIRPORTS['STL']

        # Find sites within reasonable distance (500 miles for week-long trip)
        nearby_sites = []
        for site in self.sites:
            if site.lat and site.lon:
                distance = self.haversine_distance(
                    stl['lat'], stl['lon'],
                    site.lat, site.lon
                )
                if distance <= 500:
                    nearby_sites.append((site, distance))

        print(f"Found {len(nearby_sites)} sites within 500 miles of St. Louis")

        # Take up to 20 closest sites for a week trip
        nearby_sites.sort(key=lambda x: x[1])
        selected_sites = [s[0] for s in nearby_sites[:20]]

        # Optimize route
        route = self.nearest_neighbor_route(selected_sites, stl['lat'], stl['lon'])
        stats = self.calculate_route_stats(route, stl['lat'], stl['lon'])

        # Split into 7 days
        sites_per_day = max(1, len(route) // 7)
        daily_plan = []

        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        for day in range(7):
            start_idx = day * sites_per_day
            end_idx = start_idx + sites_per_day if day < 6 else len(route)
            day_sites = route[start_idx:end_idx]

            daily_plan.append({
                'day': day + 1,
                'day_name': day_names[day],
                'sites': [
                    {
                        'name': s.name,
                        'city': s.city,
                        'state': s.state,
                        'hours': s.hours.get(day_names[day], 'Unknown'),
                        'open': s.is_open(day_names[day])
                    }
                    for s in day_sites
                ],
                'count': len(day_sites)
            })

        trip = {
            'start_location': 'St. Louis, MO',
            'days': 7,
            'total_sites': len(route),
            'stats': stats,
            'daily_plan': daily_plan
        }

        print(f"\nSt. Louis 7-day trip:")
        print(f"  Sites: {len(route)}")
        print(f"  Distance: {stats['total_distance_miles']} miles")
        print(f"  Drive time: {stats['total_drive_hours']} hours")

        return trip


def main():
    builder = ItineraryBuilder()

    # Load sites
    builder.load_sites('nps_site_inventory.json')

    # Geocode sites (limited to avoid long waits)
    builder.geocode_sites(limit=100)

    # Build 2-day trips
    print("\n" + "="*60)
    two_day_trips = builder.build_short_trips(days=2, sites_per_trip=6)

    # Build 3-day trips
    three_day_trips = builder.build_short_trips(days=3, sites_per_trip=9)

    # Build St. Louis week trip
    stl_week = builder.build_stl_week_trip()

    # Save all itineraries
    output = {
        'generated': datetime.now().isoformat(),
        'two_day_trips': two_day_trips,
        'three_day_trips': three_day_trips,
        'stl_week_trip': stl_week
    }

    with open('itineraries.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    print(f"\n{'='*60}")
    print("Saved all itineraries to itineraries.json")
    print(f"{'='*60}")

    # Create readable markdown summaries
    create_markdown_summaries(output)

    return builder


def create_markdown_summaries(output: dict):
    """Create human-readable markdown itinerary files"""

    # 2-day trips
    with open('2_day_trips.md', 'w', encoding='utf-8') as f:
        f.write("# 2-Day Airport-Based NPS Trips\n\n")
        f.write(f"Generated: {output['generated']}\n\n")

        for trip in output['two_day_trips']:
            f.write(f"## {trip['airport']}\n\n")
            f.write(f"**Duration:** {trip['days']} days | ")
            f.write(f"**Sites:** {trip['total_sites']} | ")
            f.write(f"**Distance:** {trip['stats']['total_distance_miles']} miles | ")
            f.write(f"**Drive Time:** {trip['stats']['total_drive_hours']} hours\n\n")

            for day in trip['daily_plan']:
                f.write(f"### Day {day['day']} ({day['count']} sites)\n\n")
                for site in day['sites']:
                    f.write(f"- {site}\n")
                f.write("\n")

            f.write("---\n\n")

    # 3-day trips
    with open('3_day_trips.md', 'w', encoding='utf-8') as f:
        f.write("# 3-Day Airport-Based NPS Trips\n\n")
        f.write(f"Generated: {output['generated']}\n\n")

        for trip in output['three_day_trips']:
            f.write(f"## {trip['airport']}\n\n")
            f.write(f"**Duration:** {trip['days']} days | ")
            f.write(f"**Sites:** {trip['total_sites']} | ")
            f.write(f"**Distance:** {trip['stats']['total_distance_miles']} miles | ")
            f.write(f"**Drive Time:** {trip['stats']['total_drive_hours']} hours\n\n")

            for day in trip['daily_plan']:
                f.write(f"### Day {day['day']} ({day['count']} sites)\n\n")
                for site in day['sites']:
                    f.write(f"- {site}\n")
                f.write("\n")

            f.write("---\n\n")

    # St. Louis week
    with open('stl_week_trip.md', 'w', encoding='utf-8') as f:
        f.write("# 7-Day St. Louis NPS Trip\n\n")
        f.write(f"Generated: {output['generated']}\n\n")

        trip = output['stl_week_trip']
        f.write(f"**Start:** {trip['start_location']} | ")
        f.write(f"**Duration:** {trip['days']} days | ")
        f.write(f"**Sites:** {trip['total_sites']} | ")
        f.write(f"**Distance:** {trip['stats']['total_distance_miles']} miles | ")
        f.write(f"**Drive Time:** {trip['stats']['total_drive_hours']} hours\n\n")

        for day in trip['daily_plan']:
            f.write(f"## Day {day['day']}: {day['day_name']} ({day['count']} sites)\n\n")

            for site in day['sites']:
                status = "✅ OPEN" if site['open'] else "❌ CLOSED"
                f.write(f"- **{site['name']}** ({site['city']}, {site['state']}) {status}\n")
                f.write(f"  - Hours: {site['hours']}\n")

            f.write("\n")

    print("Created markdown summaries:")
    print("  - 2_day_trips.md")
    print("  - 3_day_trips.md")
    print("  - stl_week_trip.md")


if __name__ == '__main__':
    builder = main()
