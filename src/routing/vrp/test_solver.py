#!/usr/bin/env python3
"""
Tests for VRPSolver

Tests the OR-Tools VRP setup and configuration logic.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from core.site import Site
from .solver import VRPSolver


class TestVRPSolver:
    """Tests for VRPSolver class"""

    @pytest.fixture
    def home_base(self):
        """Create home base site"""
        return Site(name="Home", lat=38.0, lon=-90.0)

    @pytest.fixture
    def sample_sites(self, home_base):
        """Create sample sites including depot"""
        return [
            home_base,
            Site(name="Site A", lat=38.1, lon=-90.1),
            Site(name="Site B", lat=38.2, lon=-90.2),
            Site(name="Site C", lat=38.3, lon=-90.3),
        ]

    @pytest.fixture
    def solver(self, sample_sites, home_base):
        """Create solver with sample sites"""
        return VRPSolver(
            sites=sample_sites,
            home_base=home_base,
            num_vehicles=2,
            max_trip_minutes=3600,
            target_trip_minutes=2700,
            avg_speed_mph=55.0,
            prioritize_range=True,
            time_limit_seconds=30,
            verbose=False
        )

    def test_solver_initialization(self, solver, home_base, sample_sites):
        """Solver should initialize with correct parameters"""
        assert solver.sites == sample_sites
        assert solver.home_base == home_base
        assert solver.num_vehicles == 2
        assert solver.max_trip_minutes == 3600
        assert solver.target_trip_minutes == 2700
        assert solver.avg_speed_mph == 55.0
        assert solver.prioritize_range is True
        assert solver.time_limit_seconds == 30
        assert solver.verbose is False

    def test_solver_with_prioritize_range_disabled(self, sample_sites, home_base):
        """Solver should accept prioritize_range=False"""
        solver = VRPSolver(
            sites=sample_sites,
            home_base=home_base,
            num_vehicles=1,
            max_trip_minutes=3600,
            target_trip_minutes=2700,
            avg_speed_mph=55.0,
            prioritize_range=False,
            verbose=False
        )

        assert solver.prioritize_range is False

    def test_solver_with_verbose_enabled(self, sample_sites, home_base):
        """Solver should accept verbose=True"""
        solver = VRPSolver(
            sites=sample_sites,
            home_base=home_base,
            num_vehicles=1,
            max_trip_minutes=3600,
            target_trip_minutes=2700,
            avg_speed_mph=55.0,
            verbose=True
        )

        assert solver.verbose is True

    def test_solver_with_single_vehicle(self, sample_sites, home_base):
        """Solver should handle single vehicle configuration"""
        solver = VRPSolver(
            sites=sample_sites,
            home_base=home_base,
            num_vehicles=1,
            max_trip_minutes=7200,
            target_trip_minutes=5400,
            avg_speed_mph=55.0,
            verbose=False
        )

        assert solver.num_vehicles == 1

    def test_solver_with_many_vehicles(self, sample_sites, home_base):
        """Solver should handle many vehicles"""
        solver = VRPSolver(
            sites=sample_sites,
            home_base=home_base,
            num_vehicles=10,
            max_trip_minutes=3600,
            target_trip_minutes=2700,
            avg_speed_mph=55.0,
            verbose=False
        )

        assert solver.num_vehicles == 10


class TestVRPSolverConfiguration:
    """Tests for VRP solver configuration methods"""

    @pytest.fixture
    def solver(self):
        """Create basic solver"""
        home_base = Site(name="Home", lat=38.0, lon=-90.0)
        sites = [
            home_base,
            Site(name="Site A", lat=38.1, lon=-90.1),
            Site(name="Site B", lat=38.2, lon=-90.2),
        ]
        return VRPSolver(
            sites=sites,
            home_base=home_base,
            num_vehicles=2,
            max_trip_minutes=3600,
            target_trip_minutes=2700,
            avg_speed_mph=55.0,
            prioritize_range=True,
            time_limit_seconds=60,
            verbose=False
        )

    @patch('vrp.solver.pywrapcp.DefaultRoutingSearchParameters')
    def test_configure_search_parameters(self, mock_params_cls, solver):
        """Should configure search parameters correctly"""
        mock_params = MagicMock()
        mock_params_cls.return_value = mock_params

        mock_routing = MagicMock()
        mock_time_limit = MagicMock()
        mock_params.time_limit = mock_time_limit

        result = solver._configure_search_parameters(mock_routing)

        assert result == mock_params
        assert mock_time_limit.seconds == 60

    @patch('vrp.solver.pywrapcp.RoutingIndexManager')
    @patch('vrp.solver.pywrapcp.RoutingModel')
    def test_create_routing_model(self, mock_routing_cls, mock_manager_cls, solver):
        """Should create routing model with correct parameters"""
        mock_manager = MagicMock()
        mock_routing = MagicMock()
        mock_manager_cls.return_value = mock_manager
        mock_routing_cls.return_value = mock_routing

        manager, routing = solver._create_routing_model()

        mock_manager_cls.assert_called_once_with(3, 2, 0)  # 3 sites, 2 vehicles, depot=0
        mock_routing_cls.assert_called_once_with(mock_manager)
        assert manager == mock_manager
        assert routing == mock_routing


class TestVRPSolverCallbacks:
    """Tests for callback registration"""

    @pytest.fixture
    def solver(self):
        """Create basic solver"""
        home_base = Site(name="Home", lat=38.0, lon=-90.0)
        sites = [
            home_base,
            Site(name="Site A", lat=38.1, lon=-90.1),
            Site(name="Site B", lat=38.2, lon=-90.2),
        ]
        return VRPSolver(
            sites=sites,
            home_base=home_base,
            num_vehicles=1,
            max_trip_minutes=3600,
            target_trip_minutes=2700,
            avg_speed_mph=55.0,
            prioritize_range=False,  # Disable for simpler testing
            verbose=False
        )

    def test_register_distance_callback_without_prioritization(self, solver):
        """Distance callback should return base distance when prioritization disabled"""
        mock_manager = MagicMock()
        mock_manager.IndexToNode.side_effect = lambda x: x
        mock_routing = MagicMock()
        mock_routing.RegisterTransitCallback.return_value = 42

        distance_matrix = [
            [0, 100, 200],
            [100, 0, 150],
            [200, 150, 0]
        ]

        callback_index = solver._register_distance_callback(
            mock_manager,
            mock_routing,
            distance_matrix
        )

        assert callback_index == 42
        assert mock_routing.RegisterTransitCallback.called

    def test_register_time_callback(self, solver):
        """Time callback should return time from matrix"""
        mock_manager = MagicMock()
        mock_manager.IndexToNode.side_effect = lambda x: x
        mock_routing = MagicMock()
        mock_routing.RegisterTransitCallback.return_value = 43

        time_matrix = [
            [0, 60, 120],
            [60, 0, 90],
            [120, 90, 0]
        ]

        callback_index = solver._register_time_callback(
            mock_manager,
            mock_routing,
            time_matrix
        )

        assert callback_index == 43
        assert mock_routing.RegisterTransitCallback.called


class TestVRPSolverEdgeCases:
    """Edge case tests for VRPSolver"""

    def test_solver_with_zero_time_limit(self):
        """Solver with zero time limit should initialize"""
        home_base = Site(name="Home", lat=38.0, lon=-90.0)
        sites = [home_base]

        solver = VRPSolver(
            sites=sites,
            home_base=home_base,
            num_vehicles=1,
            max_trip_minutes=3600,
            target_trip_minutes=2700,
            avg_speed_mph=55.0,
            time_limit_seconds=0,
            verbose=False
        )

        assert solver.time_limit_seconds == 0

    def test_solver_with_very_short_max_trip(self):
        """Solver with very short max trip should initialize"""
        home_base = Site(name="Home", lat=38.0, lon=-90.0)
        sites = [home_base]

        solver = VRPSolver(
            sites=sites,
            home_base=home_base,
            num_vehicles=1,
            max_trip_minutes=60,  # 1 hour
            target_trip_minutes=30,
            avg_speed_mph=55.0,
            verbose=False
        )

        assert solver.max_trip_minutes == 60
        assert solver.target_trip_minutes == 30

    def test_solver_with_very_long_max_trip(self):
        """Solver with very long max trip should initialize"""
        home_base = Site(name="Home", lat=38.0, lon=-90.0)
        sites = [home_base]

        solver = VRPSolver(
            sites=sites,
            home_base=home_base,
            num_vehicles=1,
            max_trip_minutes=20160,  # 2 weeks
            target_trip_minutes=10080,  # 1 week
            avg_speed_mph=55.0,
            verbose=False
        )

        assert solver.max_trip_minutes == 20160
        assert solver.target_trip_minutes == 10080

    def test_solver_with_slow_speed(self):
        """Solver with very slow average speed should initialize"""
        home_base = Site(name="Home", lat=38.0, lon=-90.0)
        sites = [home_base]

        solver = VRPSolver(
            sites=sites,
            home_base=home_base,
            num_vehicles=1,
            max_trip_minutes=3600,
            target_trip_minutes=2700,
            avg_speed_mph=25.0,  # Very slow
            verbose=False
        )

        assert solver.avg_speed_mph == 25.0

    def test_solver_with_fast_speed(self):
        """Solver with very fast average speed should initialize"""
        home_base = Site(name="Home", lat=38.0, lon=-90.0)
        sites = [home_base]

        solver = VRPSolver(
            sites=sites,
            home_base=home_base,
            num_vehicles=1,
            max_trip_minutes=3600,
            target_trip_minutes=2700,
            avg_speed_mph=75.0,  # Fast
            verbose=False
        )

        assert solver.avg_speed_mph == 75.0
