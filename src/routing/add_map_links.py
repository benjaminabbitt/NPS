#!/usr/bin/env python3
"""
Add OpenStreetMap and route planning links to trip itineraries
"""
import yaml
import json
from pathlib import Path
from typing import Dict, List


def create_osm_point_link(lat: float, lon: float, zoom: int = 15) -> str:
    """Create OpenStreetMap link for a single point"""
    return f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map={zoom}/{lat}/{lon}"


def create_osm_route_link(waypoints: List[tuple]) -> str:
    """Create OpenStreetMap Directions link with multiple waypoints"""
    # OSM format: https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=lat1,lon1;lat2,lon2;...
    route_points = ";".join([f"{lat},{lon}" for lat, lon in waypoints])
    return f"https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route={route_points}"


def create_google_maps_link(waypoints: List[tuple]) -> str:
    """Create Google Maps directions link as alternative"""
    if not waypoints:
        return ""

    # Start point
    start = waypoints[0]
    end = waypoints[-1]

    # Build URL
    url = f"https://www.google.com/maps/dir/{start[0]},{start[1]}"

    # Add intermediate waypoints
    for lat, lon in waypoints[1:-1]:
        url += f"/{lat},{lon}"

    # Add end point
    url += f"/{end[0]},{end[1]}"

    return url


def create_geojson_route(trip_data: Dict) -> Dict:
    """Create GeoJSON representation of the trip route"""
    coordinates = []
    properties = []

    for stop in trip_data['route_details']:
        coordinates.append([stop['lon'], stop['lat']])  # GeoJSON uses [lon, lat]
        properties.append({
            'name': stop['site'],
            'arrival_day': stop['day'],
            'arrival_time': stop['time_of_day']
        })

    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates
                },
                "properties": {
                    "trip_number": trip_data['trip_number'],
                    "total_sites": trip_data['stats']['total_sites'],
                    "total_distance_miles": trip_data['stats']['total_distance_miles'],
                    "total_days": trip_data['stats']['total_days']
                }
            },
            # Add points for each stop
            *[
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [stop['lon'], stop['lat']]
                    },
                    "properties": prop
                }
                for stop, prop in zip(trip_data['route_details'], properties)
            ]
        ]
    }

    return geojson


def add_map_links_to_trips(input_file: Path, output_file: Path = None):
    """Add map links to trip YAML file"""

    if output_file is None:
        output_file = input_file.parent / f"{input_file.stem}_with_maps{input_file.suffix}"

    # Load trip data
    with open(input_file) as f:
        if input_file.suffix in ['.yaml', '.yml']:
            data = yaml.safe_load(f)
        else:
            data = json.load(f)

    print(f"Processing {len(data['trips'])} trips...")

    # Add links to each trip
    for trip in data['trips']:
        print(f"\nTrip {trip['trip_number']}:")

        # Get waypoints (lat, lon tuples)
        waypoints = [(stop['lat'], stop['lon']) for stop in trip['route_details']]

        # Create various map links
        trip['map_links'] = {
            'openstreetmap_route': create_osm_route_link(waypoints),
            'google_maps_route': create_google_maps_link(waypoints),
            'geojson_viewer': f"http://geojson.io/#data=data:application/json,{json.dumps(create_geojson_route(trip))}"
        }

        # Add individual site links
        for stop in trip['route_details']:
            if stop['lat'] and stop['lon']:
                stop['osm_link'] = create_osm_point_link(stop['lat'], stop['lon'])

        print(f"  ✓ Added map links")
        print(f"    OSM Route: {trip['map_links']['openstreetmap_route'][:80]}...")

    # Save updated data
    with open(output_file, 'w') as f:
        if output_file.suffix in ['.yaml', '.yml']:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, width=120)
        else:
            json.dump(data, f, indent=2)

    # Also create standalone GeoJSON files
    geojson_dir = output_file.parent / "geojson"
    geojson_dir.mkdir(exist_ok=True)

    for trip in data['trips']:
        geojson_file = geojson_dir / f"trip_{trip['trip_number']}.geojson"
        with open(geojson_file, 'w') as f:
            json.dump(create_geojson_route(trip), f, indent=2)

    print(f"\n{'='*70}")
    print(f"COMPLETE")
    print(f"{'='*70}")
    print(f"Output file: {output_file}")
    print(f"GeoJSON files: {geojson_dir}/")
    print(f"\nYou can:")
    print(f"  1. Open {output_file} to see map links in YAML")
    print(f"  2. Upload GeoJSON files to http://geojson.io to visualize routes")
    print(f"  3. Use the OpenStreetMap links directly from the YAML file")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Add map links to trip itineraries')
    parser.add_argument('input', type=Path, help='Input YAML/JSON file with trips')
    parser.add_argument('--output', type=Path, help='Output file (default: input_with_maps.yaml)')

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: File not found: {args.input}")
        return

    add_map_links_to_trips(args.input, args.output)


if __name__ == '__main__':
    main()
