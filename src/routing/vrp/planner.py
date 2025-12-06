#!/usr/bin/env python3
"""
VRP Trip Planner

Orchestrates VRP-based trip planning using modular components:
- VRPSolver: Solves the routing problem
- TripExtractor: Extracts trips from solution
- TripValidator: Validates and resequences for operating hours
- TripReorderer: Reorders sites to fit constraints
"""

from typing import List, Tuple, Dict, Any
from pathlib import Path

from core.site import Site
from core.distance import haversine_distance
from core.time import create_time_matrix, calculate_optimal_start_hour
from constraints.operating_hours import check_site_fits_in_day
from export.map_links import create_osm_route_link, create_google_maps_link
from export.geojson import create_geojson_route

from .solver import VRPSolver
from .extractor import TripExtractor
from .validator import TripValidator
from .reorderer import TripReorderer


class VRPTripPlanner:
    """
    Multi-vehicle VRP for trip planning.

    Orchestrates modular components to:
    1. Solve VRP with distance/time optimization
    2. Extract trips from solution
    3. Validate and resequence for operating hours
    """

    def __init__(
        self,
        sites: List[Site],
        home_base: Tuple[str, float, float],
        visit_hours_per_site: float = 2.0,
        hours_per_day: int = 15,
        preferred_hours_per_day: int = 12,
        target_trip_days: int = 3,
        max_trip_days: int = 4,
        avg_speed_mph: float = 55.0,
        prioritize_range: bool = True,
        verbose: bool = False
    ):
        """
        Initialize VRP trip planner.

        Args:
            sites: List of sites to visit
            home_base: (name, lat, lon) tuple
            visit_hours_per_site: Time to spend at each site
            hours_per_day: Maximum hours per day (hard limit)
            preferred_hours_per_day: Preferred hours per day (soft limit)
            target_trip_days: Target trip duration
            max_trip_days: Maximum trip duration
            avg_speed_mph: Average travel speed
            prioritize_range: Favor distant sites
            verbose: Print detailed logging
        """
        # Setup home base
        home_name, home_lat, home_lon = home_base
        self.home_base = Site(name=home_name, lat=home_lat, lon=home_lon)

        # Store configuration
        self.sites = [self.home_base] + sites
        self.visit_minutes_per_site = int(visit_hours_per_site * 60)
        self.hours_per_day = hours_per_day
        self.preferred_hours_per_day = preferred_hours_per_day
        self.target_trip_minutes = target_trip_days * hours_per_day * 60
        self.max_trip_minutes = max_trip_days * hours_per_day * 60
        self.avg_speed_mph = avg_speed_mph
        self.prioritize_range = prioritize_range
        self.verbose = verbose

        # Trip timing
        self.earliest_start_hour = 6
        self.preferred_start_hour = 9

        # Calculate number of vehicles needed
        self.num_vehicles = self._calculate_num_vehicles(
            len(sites),
            target_trip_days,
            hours_per_day,
            visit_hours_per_site
        )

        print(f"Configuring VRP:")
        print(f"  Sites: {len(sites)}")
        print(f"  Vehicles (trips): {self.num_vehicles}")
        print(f"  Target per trip: {target_trip_days} days ({self.target_trip_minutes//60}h)")
        print(f"  Max per trip: {max_trip_days} days ({self.max_trip_minutes//60}h)")

        if self.verbose:
            self._print_verbose_config(sites, home_lat, home_lon, visit_hours_per_site)

        # Initialize components
        self._init_components()

        # Store rejected sites
        self.rejected_sites = []

    def _calculate_num_vehicles(
        self,
        num_sites: int,
        target_trip_days: int,
        hours_per_day: int,
        visit_hours_per_site: float
    ) -> int:
        """Calculate number of vehicles (trips) needed"""
        if target_trip_days <= 2:
            preferred_utilization = 0.5
            min_sites = 3
        else:
            preferred_utilization = 0.7
            min_sites = 6

        estimated_sites_per_trip = int(
            target_trip_days * hours_per_day * preferred_utilization / visit_hours_per_site
        )
        sites_per_trip = max(min_sites, estimated_sites_per_trip)
        return max(1, min(30, (num_sites + sites_per_trip - 1) // sites_per_trip))

    def _print_verbose_config(
        self,
        sites: List[Site],
        home_lat: float,
        home_lon: float,
        visit_hours_per_site: float
    ):
        """Print verbose configuration information"""
        print(f"\nVerbose mode: Detailed site information")
        print(f"  Visit time per site: {visit_hours_per_site} hours ({self.visit_minutes_per_site} min)")
        print(f"  Hours per day: {self.hours_per_day} (hard max), {self.preferred_hours_per_day} (preferred)")
        print(f"  Average speed: {self.avg_speed_mph} mph")
        print(f"  Sites loaded (first 10):")
        for i, site in enumerate(sites[:10], 1):
            dist = haversine_distance(home_lat, home_lon, site.lat, site.lon)
            print(f"    {i}. {site.name:40s} - {dist:6.1f} mi from home")

    def _init_components(self):
        """Initialize VRP solver components"""
        # Solver
        self.solver = VRPSolver(
            sites=self.sites,
            home_base=self.home_base,
            num_vehicles=self.num_vehicles,
            max_trip_minutes=self.max_trip_minutes,
            target_trip_minutes=self.target_trip_minutes,
            avg_speed_mph=self.avg_speed_mph,
            prioritize_range=self.prioritize_range,
            verbose=self.verbose
        )

        # Extractor
        self.extractor = TripExtractor(
            sites=self.sites,
            home_base=self.home_base,
            num_vehicles=self.num_vehicles,
            hours_per_day=self.hours_per_day,
            preferred_hours_per_day=self.preferred_hours_per_day,
            visit_minutes_per_site=self.visit_minutes_per_site,
            target_trip_minutes=self.target_trip_minutes,
            max_trip_minutes=self.max_trip_minutes,
            avg_speed_mph=self.avg_speed_mph,
            earliest_start_hour=self.earliest_start_hour,
            preferred_start_hour=self.preferred_start_hour,
            haversine_fn=haversine_distance,
            calculate_optimal_start_hour_fn=self._calculate_optimal_start_hour,
            verbose=self.verbose
        )

        # Reorderer
        self.reorderer = TripReorderer(
            check_site_fits_fn=self._check_site_fits_in_day
        )

        # Validator
        self.validator = TripValidator(
            home_base=self.home_base,
            hours_per_day=self.hours_per_day,
            visit_minutes_per_site=self.visit_minutes_per_site,
            max_trip_minutes=self.max_trip_minutes,
            target_trip_minutes=self.target_trip_minutes,
            avg_speed_mph=self.avg_speed_mph,
            haversine_fn=haversine_distance,
            check_site_fits_fn=self._check_site_fits_in_day,
            calculate_optimal_start_hour_fn=self._calculate_optimal_start_hour,
            try_reorder_fn=self.reorderer.try_reorder_day,
            verbose=self.verbose
        )

    def _check_site_fits_in_day(
        self,
        sites_in_day,
        new_site,
        start_location,
        day_budget_minutes,
        start_hour
    ):
        """Check if site fits in day (delegates to constraints module)"""
        return check_site_fits_in_day(
            sites_in_day,
            new_site,
            start_location,
            day_budget_minutes,
            start_hour,
            haversine_distance,
            self.avg_speed_mph,
            self.visit_minutes_per_site
        )

    def _calculate_optimal_start_hour(self, route_details):
        """Calculate optimal trip start time (delegates to core.time module)"""
        return calculate_optimal_start_hour(
            route_details,
            haversine_distance,
            self.avg_speed_mph,
            self.preferred_start_hour,
            self.earliest_start_hour
        )

    def _create_distance_matrix(self):
        """Distance matrix in meters"""
        n = len(self.sites)
        matrix = [[0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j:
                    dist_miles = haversine_distance(
                        self.sites[i].lat, self.sites[i].lon,
                        self.sites[j].lat, self.sites[j].lon
                    )
                    matrix[i][j] = int(dist_miles * 1609.34)
        return matrix

    def _create_time_matrix(self, distance_matrix):
        """Time matrix in minutes (delegates to core.time module)"""
        return create_time_matrix(
            distance_matrix,
            self.avg_speed_mph,
            self.visit_minutes_per_site
        )

    def solve(self) -> List[Dict[str, Any]]:
        """
        Solve VRP and return optimized trips.

        Returns:
            List of trip dictionaries with route details and stats
        """
        # Create matrices
        distance_matrix = self._create_distance_matrix()
        time_matrix = self._create_time_matrix(distance_matrix)

        # Solve VRP
        manager, routing, solution, time_dimension = self.solver.solve(
            distance_matrix,
            time_matrix
        )

        if not solution:
            return None

        # Extract trips from solution
        trips = self.extractor.extract_solution(
            manager,
            routing,
            solution,
            time_dimension
        )

        # Resequence trips to fit operating hours
        print(f"\nPost-processing: Resequencing trips to fit operating hours...")
        resequenced_trips = []
        all_rejected_sites = []

        for trip in trips:
            resequenced_trip, rejected_sites = self.validator.resequence_trip(trip)
            resequenced_trips.append(resequenced_trip)
            all_rejected_sites.extend(rejected_sites)

        # Report results
        if all_rejected_sites:
            print(f"\n✗ {len(all_rejected_sites)} site(s) could not be scheduled:")
            for site in all_rejected_sites:
                print(f"  - {site['name']}: {site['reason']}")
        else:
            print(f"\n✓ All sites successfully scheduled within operating hours")

        self.rejected_sites = all_rejected_sites

        # Add map links to each trip
        for trip in resequenced_trips:
            self._add_map_links(trip)

        return resequenced_trips

    def _add_map_links(self, trip: Dict[str, Any]):
        """Add OpenStreetMap and Google Maps links to trip"""
        route_details = trip['route_details']

        # Extract coordinates
        coords = [(stop['lat'], stop['lon']) for stop in route_details]

        # Create map links
        trip['map_links'] = {
            'openstreetmap_route': create_osm_route_link(coords),
            'google_maps_route': create_google_maps_link(coords)
        }
