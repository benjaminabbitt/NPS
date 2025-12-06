#!/usr/bin/env python3
"""
VRP Solver

Handles OR-Tools VRP model setup, configuration, and solving.
Implements distance-based routing with time constraints and penalties.
"""

from typing import List, Callable, Optional
from ortools.constraint_solver import routing_enums_pb2, pywrapcp
from core.site import Site


class VRPSolver:
    """
    OR-Tools VRP solver wrapper.

    Configures and solves the Vehicle Routing Problem using:
    - Distance minimization
    - Time dimension with slack
    - Soft upper bounds on trip length
    - Optional range prioritization
    """

    def __init__(
        self,
        sites: List[Site],
        home_base: Site,
        num_vehicles: int,
        max_trip_minutes: int,
        target_trip_minutes: int,
        avg_speed_mph: float,
        prioritize_range: bool = True,
        time_limit_seconds: int = 120,
        verbose: bool = False
    ):
        """
        Initialize VRP solver.

        Args:
            sites: List of all sites including depot
            home_base: Home base site (depot)
            num_vehicles: Number of vehicles (trips)
            max_trip_minutes: Hard maximum trip duration
            target_trip_minutes: Target trip duration (soft constraint)
            avg_speed_mph: Average travel speed
            prioritize_range: Favor distant sites
            time_limit_seconds: Solver time limit
            verbose: Print detailed logging
        """
        self.sites = sites
        self.home_base = home_base
        self.num_vehicles = num_vehicles
        self.max_trip_minutes = max_trip_minutes
        self.target_trip_minutes = target_trip_minutes
        self.avg_speed_mph = avg_speed_mph
        self.prioritize_range = prioritize_range
        self.time_limit_seconds = time_limit_seconds
        self.verbose = verbose

    def solve(
        self,
        distance_matrix: List[List[int]],
        time_matrix: List[List[int]]
    ):
        """
        Solve VRP with given distance and time matrices.

        Returns:
            (manager, routing, solution, time_dimension) or (None, None, None, None)
        """
        print(f"\nBuilding VRP model...")

        if self.verbose:
            self._print_matrix_info(distance_matrix, time_matrix)

        # Create routing model
        manager, routing = self._create_routing_model()

        # Register callbacks
        distance_callback_index = self._register_distance_callback(
            manager,
            routing,
            distance_matrix
        )
        time_callback_index = self._register_time_callback(
            manager,
            routing,
            time_matrix
        )

        # Set cost evaluator
        routing.SetArcCostEvaluatorOfAllVehicles(distance_callback_index)

        # Add time dimension
        time_dimension = self._add_time_dimension(routing, time_callback_index)

        # Add vehicle constraints
        self._add_vehicle_constraints(routing, time_dimension)

        # Configure search parameters
        search_parameters = self._configure_search_parameters(routing)

        # Solve
        print(f"Solving VRP (time limit: {self.time_limit_seconds}s)...")
        solution = routing.SolveWithParameters(search_parameters)

        if solution:
            if self.verbose:
                self._print_solution_info(manager, routing, solution)
            return manager, routing, solution, time_dimension
        else:
            print(f"✗ No solution found!")
            return None, None, None, None

    def _print_matrix_info(
        self,
        distance_matrix: List[List[int]],
        time_matrix: List[List[int]]
    ):
        """Print information about distance and time matrices"""
        print(f"\nVerbose: Matrix dimensions: {len(distance_matrix)}x{len(distance_matrix)}")
        print(f"Verbose: Sample distances from depot (miles):")
        for i in range(1, min(6, len(self.sites))):
            dist_miles = distance_matrix[0][i] / 1609.34
            time_hrs = time_matrix[0][i] / 60
            print(f"  To {self.sites[i].name:40s}: {dist_miles:6.1f} mi, {time_hrs:5.2f} hrs (drive+visit)")

    def _create_routing_model(self):
        """Create OR-Tools routing model"""
        manager = pywrapcp.RoutingIndexManager(
            len(self.sites),
            self.num_vehicles,
            0  # All vehicles start/end at depot
        )
        routing = pywrapcp.RoutingModel(manager)
        return manager, routing

    def _register_distance_callback(
        self,
        manager,
        routing,
        distance_matrix: List[List[int]]
    ) -> int:
        """Register distance callback with optional range prioritization"""
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            base_distance = distance_matrix[from_node][to_node]

            if self.prioritize_range and from_node != 0 and to_node != 0:
                # Reduce cost for traveling between distant sites
                from_home_dist = distance_matrix[0][from_node]
                to_home_dist = distance_matrix[0][to_node]
                avg_dist_from_home = (from_home_dist + to_home_dist) / 2

                # Apply range bonus: reduce cost by up to 30% for very distant sites
                max_distance = 500 * 1609.34  # 500 miles in meters
                range_factor = min(avg_dist_from_home / max_distance, 1.0)
                range_discount = int(base_distance * range_factor * 0.3)

                return max(1, base_distance - range_discount)

            return base_distance

        return routing.RegisterTransitCallback(distance_callback)

    def _register_time_callback(
        self,
        manager,
        routing,
        time_matrix: List[List[int]]
    ) -> int:
        """Register time callback"""
        def time_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return time_matrix[from_node][to_node]

        return routing.RegisterTransitCallback(time_callback)

    def _add_time_dimension(self, routing, time_callback_index):
        """Add time dimension to routing model"""
        routing.AddDimension(
            time_callback_index,
            300,  # 5h slack for flexibility with operating hours
            self.max_trip_minutes,  # Hard limit
            True,  # Start cumul to zero
            'Time'
        )

        time_dimension = routing.GetDimensionOrDie('Time')

        if self.verbose:
            print(f"\nVerbose: Phase 1 - Building distance-based routes (operating hours handled in Phase 2)")

        return time_dimension

    def _add_vehicle_constraints(self, routing, time_dimension):
        """Add soft upper bounds and fixed costs per vehicle"""
        # Soft upper bound on trip length
        for vehicle_id in range(self.num_vehicles):
            end_index = routing.End(vehicle_id)
            time_dimension.SetCumulVarSoftUpperBound(
                end_index,
                self.target_trip_minutes,
                100000  # Penalty for exceeding
            )

        # Small penalty for using vehicles (preference for fewer trips)
        for vehicle_id in range(self.num_vehicles):
            routing.SetFixedCostOfVehicle(50000, vehicle_id)

    def _configure_search_parameters(self, routing):
        """Configure OR-Tools search parameters"""
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = self.time_limit_seconds

        return search_parameters

    def _print_solution_info(self, manager, routing, solution):
        """Print information about found solution"""
        print(f"\nVerbose: Solution found!")
        print(f"Verbose: Objective value: {solution.ObjectiveValue()}")

        vehicles_used = sum(
            1 for v in range(self.num_vehicles)
            if routing.IsVehicleUsed(solution, v)
        )
        print(f"Verbose: Number of vehicles used: {vehicles_used}")

        # Count visited sites
        visited = set()
        for vehicle_id in range(self.num_vehicles):
            if routing.IsVehicleUsed(solution, vehicle_id):
                index = routing.Start(vehicle_id)
                while not routing.IsEnd(index):
                    node = manager.IndexToNode(index)
                    if node != 0:  # Not depot
                        visited.add(node)
                    index = solution.Value(routing.NextVar(index))

        print(f"Verbose: Sites visited: {len(visited)}/{len(self.sites)-1}")

        if len(visited) < len(self.sites) - 1:
            self._print_unvisited_sites(visited)

    def _print_unvisited_sites(self, visited: set):
        """Print information about unvisited sites"""
        from core.distance import haversine_distance

        unvisited = set(range(1, len(self.sites))) - visited
        print(f"Verbose: Unvisited sites ({len(unvisited)}):")

        for node in sorted(list(unvisited))[:20]:  # Show first 20
            site = self.sites[node]
            dist_from_home = haversine_distance(
                self.home_base.lat, self.home_base.lon,
                site.lat, site.lon
            )
            print(f"    {site.name:40s} - {dist_from_home:6.1f} mi from home")

        if len(unvisited) > 20:
            print(f"    ... and {len(unvisited) - 20} more")
