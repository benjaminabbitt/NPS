#!/usr/bin/env python3
"""
VRP-Based Trip Planner: Main entry point for multi-vehicle trip planning

Uses modular VRP components from vrp/ directory:
- VRPSolver: OR-Tools VRP model configuration and solving
- TripExtractor: Solution extraction with day-aware processing
- TripValidator: Operating hours validation and resequencing
- TripReorderer: Site reordering to fit constraints

Strategy:
- Use OR-Tools VRP with multiple vehicles (each = one trip)
- Flexible trip lengths: 3-4 days, 1 week, 2 weeks, etc.
- Configurable home base location
- 4 hours per site, 10-15 hours per day, 55 mph average speed
- Two-phase approach: distance-based routing, then operating hours resequencing

CRITICAL CONSTRAINT - Operating Hours:
- Sites MUST be visited within operating hours unless flagged with always_stamp_available
- Trips with violations are resequenced or sites are rejected
- Use optimize_trip_parameters.py to find configurations with zero violations
"""

import json
import yaml
import argparse
from pathlib import Path
from typing import Tuple

from vrp.planner import VRPTripPlanner
from unified_data_loader import UnifiedDataLoader
from core.distance import haversine_distance
from export.map_links import create_osm_route_link, create_google_maps_link
from export.geojson import create_geojson_route
from solution_output import create_solution_directory


# Default: Kirkwood, MO
DEFAULT_HOME_LAT = 38.5831
DEFAULT_HOME_LON = -90.4068
DEFAULT_HOME_NAME = "Kirkwood, MO"


def main():
    """Generate multi-trip itineraries with configurable parameters"""
    parser = argparse.ArgumentParser(description='VRP Trip Planner for all attraction types')
    parser.add_argument('--home', default=DEFAULT_HOME_NAME, help='Home base location name')
    parser.add_argument('--lat', type=float, default=DEFAULT_HOME_LAT, help='Home base latitude')
    parser.add_argument('--lon', type=float, default=DEFAULT_HOME_LON, help='Home base longitude')
    parser.add_argument('--target-days', type=int, default=3,
                        help='Target days per trip (any positive integer)')
    parser.add_argument('--max-days', type=int, help='Max days per trip (defaults to target+1)')
    parser.add_argument('--max-distance', type=int, default=500,
                        help='Maximum distance from home base in miles (default: 500, use 0 for all sites)')
    parser.add_argument('--visit-hours', type=float, default=2.0,
                        help='Hours to spend at each site (default: 2.0)')
    parser.add_argument('--hours-per-day', type=int, default=15,
                        help='Maximum working hours per day, 06:00-21:00 (default: 15)')
    parser.add_argument('--preferred-hours-per-day', type=int, default=12,
                        help='Preferred hours per day, exceeding this incurs penalties (default: 12)')
    parser.add_argument('--avg-speed', type=float, default=55.0,
                        help='Average driving speed in mph (default: 55)')
    parser.add_argument('--no-prioritize-range', action='store_true',
                        help='Disable range prioritization (default: range prioritization is enabled)')

    # Attraction type selection
    parser.add_argument('--nps', action='store_true', help='Include NPS sites (default: on)')
    parser.add_argument('--worlds-largest', action='store_true', help='Include World\'s Largest attractions')
    parser.add_argument('--parks', action='store_true', help='Include Amusement Parks')
    parser.add_argument('--all-types', action='store_true', help='Include all attraction types')
    parser.add_argument('--filter-visited', action='store_true', help='Exclude visited sites')

    parser.add_argument('--output', default='vrp_trip_itineraries.yaml', help='Output file (.json or .yaml)')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose debug logging to understand VRP solver decisions')

    args = parser.parse_args()

    # Set max days if not specified
    max_days = args.max_days if args.max_days else args.target_days + 1

    # Determine which attraction types to load
    # Default to NPS only if no types specified
    load_nps = args.nps or args.all_types or not (args.worlds_largest or args.parks)
    load_wl = args.worlds_largest or args.all_types
    load_parks = args.parks or args.all_types

    print("="*70)
    print(f"VRP TRIP PLANNER FROM {args.home.upper()}")
    print("="*70)
    print(f"Home base: {args.home} ({args.lat}, {args.lon})")
    print(f"Trip length: {args.target_days} days (max {max_days})")
    print(f"Max distance: {args.max_distance} miles" if args.max_distance > 0 else "Max distance: unlimited")
    print(f"Time per site: {args.visit_hours} hours")
    print(f"Working hours per day: {args.hours_per_day} hours (~{int(args.hours_per_day / args.visit_hours)} sites/day)")
    print(f"Average speed: {args.avg_speed} mph")

    types = []
    if load_nps: types.append("NPS")
    if load_wl: types.append("World's Largest")
    if load_parks: types.append("Amusement Parks")
    print(f"Attraction types: {', '.join(types)}")
    print()

    # Load sites using unified loader
    base_dir = Path(__file__).parent.parent.parent / "2-Enhanced Data"
    wl_file = Path(__file__).parent.parent.parent / "1-Raw Input Data/World's Largest/World's Largest.md"

    all_data = UnifiedDataLoader.load_all(
        nps_dir=base_dir / 'NPS' if load_nps else None,
        worlds_largest_file=wl_file if load_wl else None,
        parks_dir=base_dir / 'Amusement Parks' if load_parks else None,
        filter_visited=args.filter_visited
    )

    sites = all_data['all']
    print(f"Loaded {len(sites)} total sites:")
    if load_nps:
        print(f"  - NPS: {len(all_data['nps'])}")
    if load_wl:
        print(f"  - World's Largest: {len(all_data['worlds_largest'])}")
    if load_parks:
        print(f"  - Amusement Parks: {len(all_data['parks'])}")

    # Filter by distance if specified
    max_dist = args.max_distance if args.max_distance > 0 else None
    if max_dist:
        home_coords = (args.lat, args.lon)
        sites = [s for s in sites if haversine_distance(
            home_coords[0], home_coords[1], s.lat, s.lon
        ) <= max_dist]
        print(f"After distance filter ({max_dist} miles): {len(sites)} sites")

    print()

    # Create and run planner
    planner = VRPTripPlanner(
        sites=sites,
        home_base=(args.home, args.lat, args.lon),
        visit_hours_per_site=args.visit_hours,
        hours_per_day=args.hours_per_day,
        preferred_hours_per_day=args.preferred_hours_per_day,
        target_trip_days=args.target_days,
        max_trip_days=max_days,
        avg_speed_mph=args.avg_speed,
        prioritize_range=not args.no_prioritize_range,
        verbose=args.verbose
    )

    trips = planner.solve()

    if trips:
        # Generate site coverage report
        visited_sites = set()
        for trip in trips:
            for stop in trip['route_details']:
                site_name = stop.get('site_name', '')
                # Exclude home base from visited sites
                if site_name != args.home and site_name:
                    visited_sites.add(site_name)

        all_site_names = {site.name for site in sites}
        skipped_sites = all_site_names - visited_sites

        coverage_report = {
            'total_sites_in_radius': len(sites),
            'sites_visited': len(visited_sites),
            'sites_skipped': len(skipped_sites),
            'all_sites_covered': len(skipped_sites) == 0
        }

        if skipped_sites or hasattr(planner, 'rejected_sites'):
            # For each skipped site, determine reason
            skipped_details = []

            # Add rejected sites (operating hours violations) first
            if hasattr(planner, 'rejected_sites'):
                for rejected_site in planner.rejected_sites:
                    skipped_details.append({
                        'name': rejected_site['name'],
                        'reason': f"Operating hours violation: {rejected_site.get('reason', 'Unknown')}",
                        'attempted_arrival': rejected_site.get('attempted_arrival'),
                        'operating_hours': rejected_site.get('operating_hours'),
                        'lat': rejected_site.get('lat'),
                        'lon': rejected_site.get('lon')
                    })

            # Add sites that weren't included in solution at all
            for site_name in sorted(skipped_sites):
                # Skip if already in rejected sites
                if hasattr(planner, 'rejected_sites') and any(r['name'] == site_name for r in planner.rejected_sites):
                    continue

                # Find the site object
                site_obj = next((s for s in sites if s.name == site_name), None)
                if site_obj:
                    reason = "Could not fit within trip constraints (time/distance limitations)"
                    skipped_details.append({
                        'name': site_name,
                        'reason': reason,
                        'lat': site_obj.lat,
                        'lon': site_obj.lon
                    })

            if skipped_details:
                coverage_report['skipped_sites'] = skipped_details

        output = {
            'home_base': {'name': args.home, 'lat': args.lat, 'lon': args.lon},
            'parameters': {
                'visit_hours_per_site': args.visit_hours,
                'hours_per_day': args.hours_per_day,
                'preferred_hours_per_day': args.preferred_hours_per_day,
                'target_days_per_trip': args.target_days,
                'max_days_per_trip': max_days,
                'avg_speed_mph': args.avg_speed
            },
            'coverage': coverage_report,
            'trips': trips,
            'summary': {
                'total_trips': len(trips),
                'total_sites': sum(t['stats']['total_sites'] for t in trips),
                'total_distance_miles': sum(t['stats']['total_distance_miles'] for t in trips),
                'total_days': sum(t['stats']['total_days'] for t in trips)
            }
        }

        # Create solution directory with RFC3339 timestamp
        # Extract run name from output filename if provided
        output_path = Path(args.output)
        run_name = output_path.stem if output_path.stem != 'vrp_trip_itineraries' else None

        # Create timestamped solution directory
        solution_dir = create_solution_directory(run_name)
        output_file = solution_dir / output_path.name

        # Determine format based on file extension
        if output_file.suffix.lower() in ['.yaml', '.yml']:
            with open(output_file, 'w') as f:
                yaml.dump(output, f, default_flow_style=False, sort_keys=False, width=120)
        else:
            with open(output_file, 'w') as f:
                json.dump(output, f, indent=2)

        # Create GeoJSON files for map visualization
        geojson_dir = solution_dir / "geojson"
        for trip in trips:
            geojson_file = geojson_dir / f"trip_{trip['trip_number']}.geojson"
            with open(geojson_file, 'w') as f:
                json.dump(create_geojson_route(trip), f, indent=2)

        print(f"\n{'='*70}")
        print(f"RESULTS")
        print(f"{'='*70}")
        print(f"Total trips: {output['summary']['total_trips']}")
        print(f"Total sites visited: {output['summary']['total_sites']}/{len(sites)}")
        print(f"Total distance: {output['summary']['total_distance_miles']:,.0f} miles")
        print(f"Total trip days: {output['summary']['total_days']:.1f}")

        # Site coverage report
        print(f"\n{'='*70}")
        print(f"SITE COVERAGE REPORT")
        print(f"{'='*70}")
        coverage = output['coverage']
        if coverage['all_sites_covered']:
            print(f"✓ All {coverage['total_sites_in_radius']} sites within radius are included in the solution")
        else:
            print(f"⚠ {coverage['sites_visited']} of {coverage['total_sites_in_radius']} sites included")
            print(f"\nSkipped sites ({coverage['sites_skipped']}):")
            for site in coverage.get('skipped_sites', []):
                print(f"  - {site['name']}")
                print(f"    Reason: {site['reason']}")
                print(f"    Location: ({site['lat']}, {site['lon']})")

        print(f"\nPer-trip breakdown:")
        for trip in trips:
            stats = trip['stats']
            status = "✓ Target" if stats['within_target'] else ("✓ Max" if stats['within_max'] else "✗ Over")
            print(f"  Trip {trip['trip_number']}: {stats['total_sites']} sites, {stats['total_days']:.1f} days, {stats['total_distance_miles']:.0f} mi {status}")

        print(f"\n✓ Saved to {output_file}")
        print(f"✓ GeoJSON files: {geojson_dir}/")
        print(f"\nYou can:")
        print(f"  1. Open {output_file} to see trip details with map links")
        print(f"  2. Upload GeoJSON files to http://geojson.io to visualize routes")
        print(f"  3. Use the OpenStreetMap/Google Maps links from the YAML file")
        print(f"\nExample usage for other configurations:")
        print(f"  # 1-week trips:")
        print(f"  uv run python3 src/routing/vrp_trip_planner.py --target-days 7 --output weekly_trips.yaml")
        print(f"  # 2-week trips:")
        print(f"  uv run python3 src/routing/vrp_trip_planner.py --target-days 14 --output biweekly_trips.yaml")
        print(f"  # Different home base:")
        print(f"  uv run python3 src/routing/vrp_trip_planner.py --home 'Denver, CO' --lat 39.7392 --lon -104.9903")
    else:
        print("\n✗ No solution found")


if __name__ == '__main__':
    main()
