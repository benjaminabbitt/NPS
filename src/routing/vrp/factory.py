#!/usr/bin/env python3
"""
VRP Component Factory

Provides factory methods for creating VRP components with proper
dependency injection following IoC principles.
"""

from typing import List
from core.site import Site
from core.distance import haversine_distance
from core.time import calculate_optimal_start_hour
from constraints.operating_hours import check_site_fits_in_day

from .solver import VRPSolver
from .extractor import TripExtractor
from .validator import TripValidator
from .reorderer import TripReorderer


class VRPComponentFactory:
    """
    Factory for creating VRP components with proper dependency injection.

    Follows IoC principle: components don't create their own dependencies,
    they receive them from the factory.
    """

    @staticmethod
    def create_solver(
        sites: List[Site],
        home_base: Site,
        num_vehicles: int,
        max_trip_minutes: int,
        target_trip_minutes: int,
        avg_speed_mph: float,
        prioritize_range: bool = True,
        time_limit_seconds: int = 120,
        verbose: bool = False
    ) -> VRPSolver:
        """Create VRPSolver with dependencies"""  # pragma: no cover
        return VRPSolver(
            sites=sites,
            home_base=home_base,
            num_vehicles=num_vehicles,
            max_trip_minutes=max_trip_minutes,
            target_trip_minutes=target_trip_minutes,
            avg_speed_mph=avg_speed_mph,
            prioritize_range=prioritize_range,
            time_limit_seconds=time_limit_seconds,
            verbose=verbose
        )

    @staticmethod
    def create_extractor(
        sites: List[Site],
        home_base: Site,
        num_vehicles: int,
        hours_per_day: int,
        preferred_hours_per_day: int,
        visit_minutes_per_site: int,
        target_trip_minutes: int,
        max_trip_minutes: int,
        avg_speed_mph: float,
        earliest_start_hour: int,
        preferred_start_hour: int,
        calculate_optimal_start_hour_fn,
        verbose: bool = False
    ) -> TripExtractor:
        """Create TripExtractor with dependencies"""  # pragma: no cover
        return TripExtractor(
            sites=sites,
            home_base=home_base,
            num_vehicles=num_vehicles,
            hours_per_day=hours_per_day,
            preferred_hours_per_day=preferred_hours_per_day,
            visit_minutes_per_site=visit_minutes_per_site,
            target_trip_minutes=target_trip_minutes,
            max_trip_minutes=max_trip_minutes,
            avg_speed_mph=avg_speed_mph,
            earliest_start_hour=earliest_start_hour,
            preferred_start_hour=preferred_start_hour,
            haversine_fn=haversine_distance,
            calculate_optimal_start_hour_fn=calculate_optimal_start_hour_fn,
            verbose=verbose
        )

    @staticmethod
    def create_reorderer(
        check_site_fits_fn,
        max_permutation_size: int = 8
    ) -> TripReorderer:
        """Create TripReorderer with dependencies"""  # pragma: no cover
        return TripReorderer(
            check_site_fits_fn=check_site_fits_fn,
            max_permutation_size=max_permutation_size
        )

    @staticmethod
    def create_validator(
        home_base: Site,
        hours_per_day: int,
        visit_minutes_per_site: int,
        max_trip_minutes: int,
        target_trip_minutes: int,
        avg_speed_mph: float,
        check_site_fits_fn,
        calculate_optimal_start_hour_fn,
        try_reorder_fn,
        verbose: bool = False
    ) -> TripValidator:
        """Create TripValidator with dependencies"""  # pragma: no cover
        return TripValidator(
            home_base=home_base,
            hours_per_day=hours_per_day,
            visit_minutes_per_site=visit_minutes_per_site,
            max_trip_minutes=max_trip_minutes,
            target_trip_minutes=target_trip_minutes,
            avg_speed_mph=avg_speed_mph,
            haversine_fn=haversine_distance,
            check_site_fits_fn=check_site_fits_fn,
            calculate_optimal_start_hour_fn=calculate_optimal_start_hour_fn,
            try_reorder_fn=try_reorder_fn,
            verbose=verbose
        )
