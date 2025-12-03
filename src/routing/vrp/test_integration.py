#!/usr/bin/env python3
"""
Integration Tests for VRP Trip Planner

Tests the orchestration of all VRP components working together.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from core.site import Site
from .planner import VRPTripPlanner


class TestVRPTripPlannerInitialization:
    """Tests for VRPTripPlanner initialization and configuration"""

    @pytest.fixture
    def sample_sites(self):
        """Create sample sites for testing"""
        return [
            Site(name="Site A", lat=38.1, lon=-90.1),
            Site(name="Site B", lat=38.2, lon=-90.2),
            Site(name="Site C", lat=38.3, lon=-90.3),
        ]

    def test_planner_initialization(self, sample_sites):
        """Planner should initialize with correct configuration"""
        planner = VRPTripPlanner(
            sites=sample_sites,
            home_base=("Home", 38.0, -90.0),
            visit_hours_per_site=2.0,
            hours_per_day=15,
            preferred_hours_per_day=12,
            target_trip_days=3,
            max_trip_days=4,
            avg_speed_mph=55.0,
            prioritize_range=True,
            verbose=False
        )

        assert planner.home_base.name == "Home"
        assert planner.home_base.lat == 38.0
        assert planner.home_base.lon == -90.0
        assert len(planner.sites) == 4  # home + 3 sites
        assert planner.visit_minutes_per_site == 120
        assert planner.hours_per_day == 15
        assert planner.preferred_hours_per_day == 12
        assert planner.target_trip_minutes == 3 * 15 * 60
        assert planner.max_trip_minutes == 4 * 15 * 60
        assert planner.avg_speed_mph == 55.0
        assert planner.prioritize_range is True
        assert planner.verbose is False

    def test_planner_calculates_num_vehicles(self, sample_sites):
        """Planner should calculate appropriate number of vehicles"""
        planner = VRPTripPlanner(
            sites=sample_sites,
            home_base=("Home", 38.0, -90.0),
            target_trip_days=3,
            hours_per_day=15,
            visit_hours_per_site=2.0,
            verbose=False
        )

        assert planner.num_vehicles >= 1
        assert planner.num_vehicles <= 30

    def test_planner_initializes_components(self, sample_sites):
        """Planner should initialize all VRP components"""
        planner = VRPTripPlanner(
            sites=sample_sites,
            home_base=("Home", 38.0, -90.0),
            verbose=False
        )

        assert hasattr(planner, 'solver')
        assert hasattr(planner, 'extractor')
        assert hasattr(planner, 'validator')
        assert hasattr(planner, 'reorderer')
        assert planner.solver is not None
        assert planner.extractor is not None
        assert planner.validator is not None
        assert planner.reorderer is not None

    def test_planner_with_many_sites(self):
        """Planner should handle many sites"""
        many_sites = [
            Site(name=f"Site {i}", lat=38.0 + i*0.1, lon=-90.0)
            for i in range(20)
        ]
        planner = VRPTripPlanner(
            sites=many_sites,
            home_base=("Home", 38.0, -90.0),
            target_trip_days=7,
            verbose=False
        )

        assert len(planner.sites) == 21  # home + 20 sites
        assert planner.num_vehicles >= 1

    def test_planner_with_short_trips(self, sample_sites):
        """Planner should configure for short trips"""
        planner = VRPTripPlanner(
            sites=sample_sites,
            home_base=("Home", 38.0, -90.0),
            target_trip_days=1,
            max_trip_days=2,
            verbose=False
        )

        assert planner.target_trip_minutes == 1 * 15 * 60
        assert planner.max_trip_minutes == 2 * 15 * 60

    def test_planner_with_long_trips(self, sample_sites):
        """Planner should configure for long trips"""
        planner = VRPTripPlanner(
            sites=sample_sites,
            home_base=("Home", 38.0, -90.0),
            target_trip_days=14,
            max_trip_days=14,
            verbose=False
        )

        assert planner.target_trip_minutes == 14 * 15 * 60
        assert planner.max_trip_minutes == 14 * 15 * 60


class TestVRPTripPlannerMatrices:
    """Tests for distance and time matrix creation"""

    @pytest.fixture
    def planner(self):
        """Create planner with minimal sites"""
        sites = [Site(name="Site A", lat=38.1, lon=-90.1)]
        return VRPTripPlanner(
            sites=sites,
            home_base=("Home", 38.0, -90.0),
            verbose=False
        )

    def test_create_distance_matrix(self, planner):
        """Distance matrix should be created correctly"""
        matrix = planner._create_distance_matrix()

        # Should be square matrix
        assert len(matrix) == len(planner.sites)
        assert all(len(row) == len(planner.sites) for row in matrix)

        # Diagonal should be zero
        for i in range(len(matrix)):
            assert matrix[i][i] == 0

        # Should be symmetric
        for i in range(len(matrix)):
            for j in range(len(matrix)):
                assert matrix[i][j] == matrix[j][i]

    def test_create_time_matrix(self, planner):
        """Time matrix should be created from distance matrix"""
        distance_matrix = planner._create_distance_matrix()
        time_matrix = planner._create_time_matrix(distance_matrix)

        # Should be same dimensions
        assert len(time_matrix) == len(distance_matrix)
        assert all(len(row) == len(distance_matrix) for row in time_matrix)

        # All entries should be non-negative
        for row in time_matrix:
            assert all(t >= 0 for t in row)

    def test_distance_matrix_with_multiple_sites(self):
        """Distance matrix should handle multiple sites"""
        sites = [
            Site(name="Site A", lat=38.1, lon=-90.1),
            Site(name="Site B", lat=38.2, lon=-90.2),
            Site(name="Site C", lat=38.3, lon=-90.3),
        ]
        planner = VRPTripPlanner(
            sites=sites,
            home_base=("Home", 38.0, -90.0),
            verbose=False
        )

        matrix = planner._create_distance_matrix()

        # 4 sites total (home + 3)
        assert len(matrix) == 4
        # All entries should be non-negative
        for row in matrix:
            assert all(d >= 0 for d in row)


class TestVRPTripPlannerHelpers:
    """Tests for helper methods"""

    @pytest.fixture
    def planner(self):
        """Create basic planner"""
        sites = [Site(name="Site A", lat=38.1, lon=-90.1)]
        return VRPTripPlanner(
            sites=sites,
            home_base=("Home", 38.0, -90.0),
            verbose=False
        )

    def test_calculate_num_vehicles_short_trip(self, planner):
        """Short trips should calculate vehicles correctly"""
        num_vehicles = planner._calculate_num_vehicles(
            num_sites=5,
            target_trip_days=2,
            hours_per_day=15,
            visit_hours_per_site=2.0
        )

        assert num_vehicles >= 1
        assert num_vehicles <= 30

    def test_calculate_num_vehicles_long_trip(self, planner):
        """Long trips should calculate vehicles correctly"""
        num_vehicles = planner._calculate_num_vehicles(
            num_sites=20,
            target_trip_days=7,
            hours_per_day=15,
            visit_hours_per_site=2.0
        )

        assert num_vehicles >= 1
        assert num_vehicles <= 30

    def test_calculate_num_vehicles_many_sites(self, planner):
        """Many sites should calculate vehicles correctly"""
        num_vehicles = planner._calculate_num_vehicles(
            num_sites=100,
            target_trip_days=3,
            hours_per_day=15,
            visit_hours_per_site=2.0
        )

        assert num_vehicles >= 1
        # Should cap at 30 vehicles
        assert num_vehicles <= 30

    def test_calculate_num_vehicles_few_sites(self, planner):
        """Few sites should calculate at least 1 vehicle"""
        num_vehicles = planner._calculate_num_vehicles(
            num_sites=1,
            target_trip_days=3,
            hours_per_day=15,
            visit_hours_per_site=2.0
        )

        assert num_vehicles >= 1


class TestVRPTripPlannerIntegration:
    """End-to-end integration tests"""

    @pytest.fixture
    def sample_sites(self):
        """Create sample sites"""
        return [
            Site(name="Site A", lat=38.1, lon=-90.1),
            Site(name="Site B", lat=38.2, lon=-90.2),
        ]

    @patch('vrp.planner.VRPSolver')
    @patch('vrp.planner.TripExtractor')
    @patch('vrp.planner.TripValidator')
    def test_solve_returns_none_when_no_solution(
        self,
        mock_validator_cls,
        mock_extractor_cls,
        mock_solver_cls,
        sample_sites
    ):
        """Solve should return None when solver finds no solution"""
        # Setup mocks
        mock_solver = MagicMock()
        mock_solver.solve.return_value = (None, None, None, None)
        mock_solver_cls.return_value = mock_solver

        mock_extractor_cls.return_value = MagicMock()
        mock_validator_cls.return_value = MagicMock()

        planner = VRPTripPlanner(
            sites=sample_sites,
            home_base=("Home", 38.0, -90.0),
            verbose=False
        )

        result = planner.solve()

        assert result is None

    @patch('vrp.planner.VRPSolver')
    @patch('vrp.planner.TripExtractor')
    @patch('vrp.planner.TripValidator')
    def test_solve_orchestrates_components(
        self,
        mock_validator_cls,
        mock_extractor_cls,
        mock_solver_cls,
        sample_sites
    ):
        """Solve should orchestrate all components"""
        # Setup mock solver
        mock_solver = MagicMock()
        mock_manager = MagicMock()
        mock_routing = MagicMock()
        mock_solution = MagicMock()
        mock_time_dim = MagicMock()
        mock_solver.solve.return_value = (
            mock_manager,
            mock_routing,
            mock_solution,
            mock_time_dim
        )
        mock_solver_cls.return_value = mock_solver

        # Setup mock extractor
        mock_extractor = MagicMock()
        mock_trip = {
            'trip_number': 1,
            'route_details': [
                {'site_name': 'Home', 'lat': 38.0, 'lon': -90.0},
                {'site_name': 'Site A', 'lat': 38.1, 'lon': -90.1},
                {'site_name': 'Home', 'lat': 38.0, 'lon': -90.0}
            ],
            'stats': {'total_sites': 1}
        }
        mock_extractor.extract_solution.return_value = [mock_trip]
        mock_extractor_cls.return_value = mock_extractor

        # Setup mock validator
        mock_validator = MagicMock()
        resequenced_trip = mock_trip.copy()
        mock_validator.resequence_trip.return_value = (resequenced_trip, [])
        mock_validator_cls.return_value = mock_validator

        planner = VRPTripPlanner(
            sites=sample_sites,
            home_base=("Home", 38.0, -90.0),
            verbose=False
        )

        result = planner.solve()

        # Verify component calls
        assert mock_solver.solve.called
        assert mock_extractor.extract_solution.called
        assert mock_validator.resequence_trip.called
        assert result is not None
        assert len(result) == 1


class TestVRPTripPlannerEdgeCases:
    """Edge case tests for VRP planner"""

    def test_planner_with_single_site(self):
        """Planner should handle single site"""
        sites = [Site(name="Only Site", lat=38.1, lon=-90.1)]
        planner = VRPTripPlanner(
            sites=sites,
            home_base=("Home", 38.0, -90.0),
            verbose=False
        )

        assert len(planner.sites) == 2  # home + 1 site
        assert planner.num_vehicles >= 1

    def test_planner_with_zero_preferred_hours(self):
        """Planner should handle zero preferred hours"""
        sites = [Site(name="Site A", lat=38.1, lon=-90.1)]
        planner = VRPTripPlanner(
            sites=sites,
            home_base=("Home", 38.0, -90.0),
            preferred_hours_per_day=0,
            verbose=False
        )

        assert planner.preferred_hours_per_day == 0

    def test_planner_verbose_mode(self):
        """Planner should accept verbose mode"""
        sites = [Site(name="Site A", lat=38.1, lon=-90.1)]
        planner = VRPTripPlanner(
            sites=sites,
            home_base=("Home", 38.0, -90.0),
            verbose=True
        )

        assert planner.verbose is True
