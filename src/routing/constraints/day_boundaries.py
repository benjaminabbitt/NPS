#!/usr/bin/env python3
"""
Day boundary constraints for trip planning

Constants and functions for managing trip timing, day budgets,
and trip duration calculations.
"""
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class TripTiming:
    """
    Trip timing configuration.

    All times are in hours unless otherwise specified.
    """
    # Day boundaries
    earliest_start_hour: int = 6   # Earliest trip start (6am)
    latest_end_hour: int = 21      # Latest trip end (9pm)
    preferred_start_hour: int = 9  # Preferred start time (9am)

    # Day budget
    hours_per_day: int = 15        # Maximum: 06:00-21:00 operating window
    preferred_hours_per_day: int = 12  # Preferred limit (soft, with penalties)

    # Site visit duration
    visit_hours_per_site: float = 4.0  # Time per site (stamps + exploration)

    # Travel parameters
    avg_speed_mph: float = 55.0    # Average driving speed

    @property
    def visit_minutes_per_site(self) -> int:
        """Visit time in minutes"""
        return int(self.visit_hours_per_site * 60)

    @property
    def earliest_start_minutes(self) -> int:
        """Earliest start in minutes since midnight"""
        return self.earliest_start_hour * 60

    @property
    def preferred_start_minutes(self) -> int:
        """Preferred start in minutes since midnight"""
        return self.preferred_start_hour * 60

    @property
    def day_budget_minutes(self) -> int:
        """Maximum day budget in minutes"""
        return self.hours_per_day * 60

    @property
    def preferred_day_budget_minutes(self) -> int:
        """Preferred day budget in minutes"""
        return self.preferred_hours_per_day * 60


def calculate_trip_capacity(
    target_days: int,
    hours_per_day: int,
    visit_hours_per_site: float,
    utilization: float = 0.7
) -> int:
    """
    Calculate estimated sites per trip based on time budget.

    Args:
        target_days: Target trip duration (days)
        hours_per_day: Working hours per day
        visit_hours_per_site: Time to spend at each site
        utilization: Percentage of time spent visiting (vs driving)

    Returns:
        Estimated number of sites that fit in trip

    Examples:
        >>> calculate_trip_capacity(3, 12, 4.0, 0.7)
        6
        >>> calculate_trip_capacity(7, 12, 4.0, 0.7)
        14
    """
    total_hours = target_days * hours_per_day
    effective_hours = total_hours * utilization
    sites = int(effective_hours / visit_hours_per_site)
    return max(1, sites)


def calculate_num_vehicles(
    num_sites: int,
    sites_per_trip: int,
    max_vehicles: int = 30
) -> int:
    """
    Calculate number of vehicles (trips) needed to cover all sites.

    Args:
        num_sites: Total number of sites to visit
        sites_per_trip: Target sites per trip
        max_vehicles: Maximum allowed vehicles

    Returns:
        Number of vehicles needed (1-max_vehicles)

    Examples:
        >>> calculate_num_vehicles(20, 5)
        4
        >>> calculate_num_vehicles(100, 10)
        10
        >>> calculate_num_vehicles(1000, 10)  # Capped at max
        30
    """
    if num_sites == 0:
        return 1

    vehicles = (num_sites + sites_per_trip - 1) // sites_per_trip
    return max(1, min(max_vehicles, vehicles))


def calculate_trip_metrics(
    target_days: int,
    max_days: int,
    hours_per_day: int
) -> Tuple[int, int]:
    """
    Calculate trip duration budgets in minutes.

    Args:
        target_days: Target trip duration
        max_days: Maximum trip duration
        hours_per_day: Hours per day

    Returns:
        (target_minutes, max_minutes) tuple

    Examples:
        >>> calculate_trip_metrics(3, 4, 15)
        (2700, 3600)
        >>> calculate_trip_metrics(7, 10, 12)
        (5040, 7200)
    """
    target_minutes = target_days * hours_per_day * 60
    max_minutes = max_days * hours_per_day * 60
    return target_minutes, max_minutes


if __name__ == '__main__':
    # Quick validation
    print("Testing TripTiming dataclass...")

    # Test 1: Default timing
    timing = TripTiming()
    assert timing.earliest_start_hour == 6
    assert timing.preferred_start_hour == 9
    assert timing.hours_per_day == 15
    print("  ✓ Default timing configuration")

    # Test 2: Computed properties
    assert timing.visit_minutes_per_site == 240  # 4 hours * 60
    assert timing.earliest_start_minutes == 360  # 6 * 60
    assert timing.preferred_start_minutes == 540  # 9 * 60
    assert timing.day_budget_minutes == 900  # 15 * 60
    print("  ✓ Computed properties correct")

    # Test 3: Custom timing
    custom = TripTiming(
        visit_hours_per_site=2.0,
        hours_per_day=12,
        preferred_hours_per_day=10
    )
    assert custom.visit_minutes_per_site == 120
    assert custom.day_budget_minutes == 720
    assert custom.preferred_day_budget_minutes == 600
    print("  ✓ Custom timing configuration")

    print("✓ TripTiming validated")

    print("\nTesting calculate_trip_capacity...")

    # Test 1: 3-day trip
    capacity = calculate_trip_capacity(3, 12, 4.0, 0.7)
    assert capacity == 6, f"Expected 6, got {capacity}"
    print(f"  ✓ 3-day trip: {capacity} sites")

    # Test 2: 7-day trip
    capacity = calculate_trip_capacity(7, 12, 4.0, 0.7)
    assert capacity == 14, f"Expected 14, got {capacity}"
    print(f"  ✓ 7-day trip: {capacity} sites")

    # Test 3: Edge case - very short trip
    capacity = calculate_trip_capacity(1, 12, 4.0, 0.7)
    assert capacity >= 1  # Should return at least 1
    print(f"  ✓ 1-day trip: {capacity} sites")

    print("✓ Trip capacity calculation validated")

    print("\nTesting calculate_num_vehicles...")

    # Test 1: Exact division
    vehicles = calculate_num_vehicles(20, 5)
    assert vehicles == 4
    print(f"  ✓ 20 sites, 5 per trip: {vehicles} vehicles")

    # Test 2: Remainder
    vehicles = calculate_num_vehicles(23, 5)
    assert vehicles == 5
    print(f"  ✓ 23 sites, 5 per trip: {vehicles} vehicles")

    # Test 3: Max cap
    vehicles = calculate_num_vehicles(1000, 10)
    assert vehicles == 30
    print(f"  ✓ 1000 sites capped at: {vehicles} vehicles")

    # Test 4: Zero sites
    vehicles = calculate_num_vehicles(0, 5)
    assert vehicles == 1
    print(f"  ✓ 0 sites: {vehicles} vehicle")

    print("✓ Vehicle calculation validated")

    print("\nTesting calculate_trip_metrics...")

    # Test 1: 3-day trip
    target, max_time = calculate_trip_metrics(3, 4, 15)
    assert target == 2700  # 3 * 15 * 60
    assert max_time == 3600  # 4 * 15 * 60
    print(f"  ✓ 3-4 day trip: target={target}min, max={max_time}min")

    # Test 2: 7-day trip
    target, max_time = calculate_trip_metrics(7, 10, 12)
    assert target == 5040  # 7 * 12 * 60
    assert max_time == 7200  # 10 * 12 * 60
    print(f"  ✓ 7-10 day trip: target={target}min, max={max_time}min")

    print("✓ Trip metrics calculation validated")
