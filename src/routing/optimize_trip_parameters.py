#!/usr/bin/env python3
"""
Optimize trip planning parameters to minimize operating hours violations
while maximizing site coverage.

This script iterates through different parameter combinations to find
the optimal balance between:
- Maximum sites covered
- Minimum trips required
- Minimum operating hours violations
- Target trip duration compliance
"""
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class OptimizationResult:
    """Results from a single parameter configuration"""
    max_distance: int
    target_days: int
    total_sites: int
    total_trips: int
    total_violations: int
    violation_rate: float
    avg_trip_days: float
    within_target_count: int
    output_file: str

    def score(self) -> float:
        """
        Calculate optimization score (higher is better)

        Priorities:
        1. Minimize violation rate (most important)
        2. Maximize sites covered
        3. Minimize trips
        4. Stay within target days
        """
        # Penalty for violations (0-100 points, lower is better)
        violation_penalty = self.violation_rate * 100

        # Reward for sites covered (0-100 points)
        sites_score = min(100, (self.total_sites / 50) * 100)

        # Penalty for too many trips (0-50 points)
        trips_penalty = min(50, self.total_trips * 5)

        # Reward for staying within target (0-50 points)
        target_score = (self.within_target_count / max(1, self.total_trips)) * 50

        # Combined score: maximize sites and target compliance, minimize violations and trips
        return sites_score + target_score - violation_penalty - trips_penalty


class TripParameterOptimizer:
    """Optimize trip planning parameters"""

    def __init__(self, planner_script: Path = Path("src/routing/vrp_trip_planner.py")):
        self.planner_script = planner_script
        self.results: List[OptimizationResult] = []

    def run_configuration(
        self,
        max_distance: int,
        target_days: int,
        output_dir: Path = Path("optimization_results")
    ) -> OptimizationResult:
        """Run trip planner with specific parameters and analyze results"""
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / f"dist{max_distance}_days{target_days}.yaml"

        # Run trip planner with new defaults (2 hours/site, 10 hours/day)
        cmd = [
            "python3", str(self.planner_script),
            "--target-days", str(target_days),
            "--max-distance", str(max_distance),
            "--visit-hours", "2.0",
            "--hours-per-day", "10",
            "--output", str(output_file)
        ]

        print(f"\nTesting: {max_distance}mi, {target_days} days...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0 or "No solution found" in result.stdout:
            print(f"  ✗ No solution found")
            return None

        # Analyze output file
        with open(output_file) as f:
            import yaml
            data = yaml.safe_load(f)

        # Count violations (only VIOLATION type, not INFO for always-available sites)
        violations = 0
        total_sites = 0
        for trip in data['trips']:
            for stop in trip['route_details']:
                # Skip depot (Kirkwood)
                if stop.get('site_name') != 'Kirkwood, MO':
                    total_sites += 1
                    # Only count VIOLATION warnings (not INFO for always_stamp_available sites)
                    if 'time_constraint_warning' in stop:
                        warning = stop['time_constraint_warning']
                        if warning.startswith('[VIOLATION]'):
                            violations += 1

        # Remove duplicate sites (return to home counted twice)
        total_sites = data['summary']['total_sites']
        total_trips = data['summary']['total_trips']

        # Count trips within target
        within_target = sum(
            1 for trip in data['trips']
            if trip['stats'].get('within_target', False)
        )

        avg_days = data['summary']['total_days'] / total_trips if total_trips > 0 else 0
        violation_rate = violations / total_sites if total_sites > 0 else 0

        result = OptimizationResult(
            max_distance=max_distance,
            target_days=target_days,
            total_sites=total_sites,
            total_trips=total_trips,
            total_violations=violations,
            violation_rate=violation_rate,
            avg_trip_days=avg_days,
            within_target_count=within_target,
            output_file=str(output_file)
        )

        print(f"  Sites: {total_sites}, Trips: {total_trips}, "
              f"Violations: {violations}/{total_sites} ({violation_rate:.1%}), "
              f"Score: {result.score():.1f}")

        return result

    def optimize(
        self,
        distance_range: Tuple[int, int] = (100, 600),
        target_days: int = 3,
        max_days: int = 4
    ) -> OptimizationResult:
        """
        Find optimal parameters using binary search for maximum coverage with zero violations

        Strategy:
        1. Binary search to find maximum distance with zero violations
        2. This maximizes site coverage while respecting operating hours

        Args:
            distance_range: (min_distance, max_distance)
            target_days: Target days per trip
            max_days: Maximum days per trip

        Returns:
            Best configuration with zero violations
        """
        min_dist, max_dist = distance_range
        best_zero_violation = None

        print("="*70)
        print("TRIP PARAMETER OPTIMIZATION - Binary Search")
        print("="*70)
        print(f"Goal: Find maximum distance with ZERO violations")
        print(f"Distance range: {min_dist}-{max_dist} miles")
        print(f"Target days: {target_days} (max: {max_days})")
        print()

        # Binary search for maximum distance with zero violations
        left, right = min_dist, max_dist

        while left <= right:
            mid = (left + right) // 2
            print(f"\nBinary search: Testing {mid} miles (range: {left}-{right})")

            result = self.run_configuration(mid, target_days)

            if result is None:
                # No solution found, try smaller distance
                print(f"  No solution found, trying smaller distance")
                right = mid - 1
                continue

            self.results.append(result)

            if result.total_violations == 0:
                # Zero violations! Try to go larger
                print(f"  ✓ Zero violations with {result.total_sites} sites - trying larger distance")
                best_zero_violation = result
                left = mid + 1
            else:
                # Has violations, try smaller distance
                print(f"  ✗ {result.total_violations} violations - trying smaller distance")
                right = mid - 1

        if best_zero_violation:
            print(f"\n{'='*70}")
            print(f"FOUND: Maximum distance with zero violations = {best_zero_violation.max_distance} miles")
            print(f"Coverage: {best_zero_violation.total_sites} sites in {best_zero_violation.total_trips} trips")
            print(f"{'='*70}")
        else:
            print(f"\n{'='*70}")
            print(f"WARNING: No configuration found with zero violations!")
            print(f"Consider:")
            print(f"  1. Marking some sites as always_stamp_available")
            print(f"  2. Accepting longer trips (more days)")
            print(f"  3. Manual itinerary adjustment")
            print(f"{'='*70}")

            # Fall back to best available (minimum violations)
            if self.results:
                best_zero_violation = min(self.results, key=lambda r: r.violation_rate)
                print(f"\nBest available: {best_zero_violation.max_distance}mi with {best_zero_violation.total_violations} violations")

        return best_zero_violation

    def print_summary(self, best_result: OptimizationResult):
        """Print optimization summary"""
        print("\n" + "="*70)
        print("OPTIMIZATION COMPLETE")
        print("="*70)

        if not best_result:
            print("No valid configurations found!")
            return

        print(f"\nBest Configuration:")
        print(f"  Maximum distance: {best_result.max_distance} miles")
        print(f"  Target trip days: {best_result.target_days}")
        print(f"  Total sites covered: {best_result.total_sites}")
        print(f"  Total trips: {best_result.total_trips}")
        print(f"  Operating hours violations: {best_result.total_violations}/{best_result.total_sites} ({best_result.violation_rate:.1%})")
        print(f"  Average trip length: {best_result.avg_trip_days:.1f} days")
        print(f"  Trips within target: {best_result.within_target_count}/{best_result.total_trips}")
        print(f"  Optimization score: {best_result.score():.1f}")
        print(f"\nOutput file: {best_result.output_file}")

        # Show top 5 configurations
        print(f"\nTop 5 Configurations:")
        sorted_results = sorted(self.results, key=lambda r: r.score(), reverse=True)[:5]
        for i, result in enumerate(sorted_results, 1):
            print(f"  {i}. {result.max_distance}mi, {result.target_days}d: "
                  f"{result.total_sites} sites, {result.total_trips} trips, "
                  f"{result.violation_rate:.1%} violations (score: {result.score():.1f})")


def calculate_default_max_distance(target_days: int) -> int:
    """
    Calculate default maximum distance based on trip duration.

    Formula:
    1. Realistic max = (days * hours_per_day * avg_speed) * 0.5
       - Assumes 50% of time is driving, 50% is visiting sites
    2. Conservative upper bound = realistic_max / 2
       - Provides buffer for operating hours constraints and inefficiencies

    Final: max_distance = days * hours_per_day * avg_speed * 0.25

    Parameters from vrp_trip_planner.py (updated 2025-11-23):
    - hours_per_day: 10 working hours (6 AM - 4 PM for realistic pacing)
    - avg_speed: 55 mph
    - visit_hours_per_site: 4 hours (~2 sites per day)

    Args:
        target_days: Number of days for the trip

    Returns:
        Conservative maximum distance in miles

    Examples:
        3 days:  3 * 10 * 55 * 0.25 = 412 miles
        7 days:  7 * 10 * 55 * 0.25 = 962 miles
        14 days: 14 * 10 * 55 * 0.25 = 1,925 miles
    """
    HOURS_PER_DAY = 10  # Updated from 12 to 10 for realistic pacing
    AVG_SPEED_MPH = 55
    CONSERVATIVE_FACTOR = 0.25  # 50% driving time, then halved for safety

    return int(target_days * HOURS_PER_DAY * AVG_SPEED_MPH * CONSERVATIVE_FACTOR)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Optimize trip planning parameters using binary search for zero violations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Default max-distance calculation:
  max_distance = target_days * 10 hours/day * 55 mph * 0.25

  Examples:
    3 days:  412 miles
    7 days:  962 miles
    14 days: 1,925 miles

  This assumes 50% of time is driving, then halved for safety margin.
  Updated 2025-11-23: hours_per_day reduced from 12 to 10 for realistic pacing.
        """
    )
    parser.add_argument('--min-distance', type=int, default=50,
                        help='Minimum distance to test (default: 50)')
    parser.add_argument('--max-distance', type=int, default=None,
                        help='Maximum distance to test (default: auto-calculated from target-days)')
    parser.add_argument('--target-days', type=int, default=3,
                        help='Target days per trip (default: 3)')

    args = parser.parse_args()

    # Calculate default max distance if not provided
    if args.max_distance is None:
        args.max_distance = calculate_default_max_distance(args.target_days)
        print(f"Auto-calculated max-distance: {args.max_distance} miles (for {args.target_days} days)")
        print()

    optimizer = TripParameterOptimizer()
    best = optimizer.optimize(
        distance_range=(args.min_distance, args.max_distance),
        target_days=args.target_days
    )

    optimizer.print_summary(best)

    if best:
        if best.total_violations == 0:
            print(f"\n✓ Optimal configuration found with ZERO violations!")
        else:
            print(f"\n⚠ Best available has {best.total_violations} violations")
            print(f"  Consider manual adjustment or marking sites as always_stamp_available")

        print(f"\nTo use this configuration:")
        print(f"  python3 src/routing/vrp_trip_planner.py --target-days {best.target_days} "
              f"--max-distance {best.max_distance} --output optimal_trips.yaml")


if __name__ == '__main__':
    main()
