#!/usr/bin/env python3
"""
GeoJSON route generation for trip visualization

Pure functions for creating GeoJSON representations of trip routes
compatible with geojson.io and other mapping tools.
"""
from typing import Dict, List


def create_geojson_route(trip_data: Dict) -> Dict:
    """
    Create GeoJSON FeatureCollection representing a trip route.

    Generates:
    - LineString feature for the route path
    - Point features for each stop

    Args:
        trip_data: Dictionary containing:
            - trip_number: int
            - route_details: List of stops with lat, lon, site, day, time_of_day
            - stats: Dict with total_sites, total_distance_miles, total_days

    Returns:
        GeoJSON FeatureCollection with LineString and Point features

    Examples:
        >>> trip_data = {
        ...     'trip_number': 1,
        ...     'route_details': [
        ...         {'site': 'Home', 'lat': 38.5831, 'lon': -90.4068,
        ...          'day': 1, 'time_of_day': '09:00'},
        ...         {'site': 'Site 1', 'lat': 38.6247, 'lon': -90.1848,
        ...          'day': 1, 'time_of_day': '10:30'}
        ...     ],
        ...     'stats': {
        ...         'total_sites': 1,
        ...         'total_distance_miles': 10.5,
        ...         'total_days': 1
        ...     }
        ... }
        >>> geojson = create_geojson_route(trip_data)
        >>> geojson['type']
        'FeatureCollection'
        >>> len(geojson['features'])  # 1 LineString + 2 Points
        3
        >>> geojson['features'][0]['geometry']['type']
        'LineString'
    """
    coordinates = []
    properties = []

    for stop in trip_data['route_details']:
        # GeoJSON uses [lon, lat] order (not [lat, lon])
        coordinates.append([stop['lon'], stop['lat']])
        properties.append({
            'name': stop['site'],
            'arrival_day': stop['day'],
            'arrival_time': stop['time_of_day']
        })

    geojson = {
        "type": "FeatureCollection",
        "features": [
            # LineString feature for the route path
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
            # Point features for each stop
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


if __name__ == '__main__':
    # Quick validation
    print("Testing create_geojson_route...")

    trip_data = {
        'trip_number': 1,
        'route_details': [
            {'site': 'Home', 'lat': 38.5831, 'lon': -90.4068, 'day': 1, 'time_of_day': '09:00'},
            {'site': 'Site 1', 'lat': 38.6247, 'lon': -90.1848, 'day': 1, 'time_of_day': '10:30'},
            {'site': 'Site 2', 'lat': 38.6270, 'lon': -90.1994, 'day': 1, 'time_of_day': '12:00'}
        ],
        'stats': {
            'total_sites': 2,
            'total_distance_miles': 15.2,
            'total_days': 1
        }
    }

    geojson = create_geojson_route(trip_data)

    # Test 1: Basic structure
    assert geojson['type'] == 'FeatureCollection'
    assert 'features' in geojson
    print("  ✓ Has FeatureCollection structure")

    # Test 2: Feature count (1 LineString + 3 Points = 4 features)
    assert len(geojson['features']) == 4
    print("  ✓ Has correct number of features (1 LineString + 3 Points)")

    # Test 3: LineString feature
    line_feature = geojson['features'][0]
    assert line_feature['type'] == 'Feature'
    assert line_feature['geometry']['type'] == 'LineString'
    assert len(line_feature['geometry']['coordinates']) == 3
    # GeoJSON uses [lon, lat] order
    assert line_feature['geometry']['coordinates'][0] == [-90.4068, 38.5831]
    print("  ✓ LineString feature correct")

    # Test 4: Point features
    point_feature = geojson['features'][1]
    assert point_feature['type'] == 'Feature'
    assert point_feature['geometry']['type'] == 'Point'
    assert point_feature['properties']['name'] == 'Home'
    print("  ✓ Point features correct")

    # Test 5: Properties
    assert line_feature['properties']['trip_number'] == 1
    assert line_feature['properties']['total_sites'] == 2
    assert line_feature['properties']['total_distance_miles'] == 15.2
    print("  ✓ Properties correct")

    print("✓ GeoJSON generation validated")

    # Output sample for manual inspection
    import json
    print("\nSample GeoJSON output:")
    print(json.dumps(geojson, indent=2)[:500] + "...")
