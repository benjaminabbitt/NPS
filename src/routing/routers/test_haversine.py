"""Tests for HaversineRouter"""
import pytest
import math
from .haversine import HaversineRouter
from .base import DistanceSource


class TestHaversineRouterProperties:
    """Tests for HaversineRouter properties"""

    def test_name_includes_speed(self):
        router = HaversineRouter(avg_speed_mph=55.0)
        assert "55.0 mph" in router.name
        assert "Haversine" in router.name

    def test_name_reflects_custom_speed(self):
        router = HaversineRouter(avg_speed_mph=65.0)
        assert "65.0 mph" in router.name

    def test_source_is_haversine(self):
        router = HaversineRouter()
        assert router.source == DistanceSource.HAVERSINE

    def test_is_estimated_always_true(self):
        router = HaversineRouter()
        assert router.is_estimated is True

    def test_default_speed_is_55(self):
        router = HaversineRouter()
        assert router.avg_speed_mph == 55.0

    def test_custom_speed(self):
        router = HaversineRouter(avg_speed_mph=70.0)
        assert router.avg_speed_mph == 70.0


class TestHaversineDistance:
    """Tests for Haversine distance calculations"""

    @pytest.fixture
    def router(self):
        return HaversineRouter(avg_speed_mph=55.0)

    def test_same_point_returns_zero_distance(self, router):
        result = router.get_route((38.5831, -90.4068), (38.5831, -90.4068))
        assert result.distance_miles == 0.0

    def test_same_point_returns_zero_duration(self, router):
        result = router.get_route((38.5831, -90.4068), (38.5831, -90.4068))
        assert result.duration_minutes == 0.0

    def test_kirkwood_to_louisville_distance(self, router):
        # Kirkwood, MO to Louisville, KY - approximately 250-260 miles straight line
        result = router.get_route(
            (38.5831, -90.4068),   # Kirkwood, MO
            (38.2527, -85.7585)    # Louisville, KY
        )
        assert 250 < result.distance_miles < 270

    def test_kirkwood_to_louisville_duration_derived_from_distance(self, router):
        result = router.get_route(
            (38.5831, -90.4068),
            (38.2527, -85.7585)
        )
        expected_duration = (result.distance_miles / 55.0) * 60.0
        assert abs(result.duration_minutes - expected_duration) < 0.01

    def test_new_york_to_los_angeles(self, router):
        # NYC to LA - approximately 2450 miles straight line
        result = router.get_route(
            (40.7128, -74.0060),   # New York
            (34.0522, -118.2437)   # Los Angeles
        )
        assert 2400 < result.distance_miles < 2500

    def test_result_source_is_haversine(self, router):
        result = router.get_route((0, 0), (1, 1))
        assert result.source == DistanceSource.HAVERSINE

    def test_result_is_estimated_true(self, router):
        result = router.get_route((0, 0), (1, 1))
        assert result.is_estimated is True

    def test_result_contains_origin_destination(self, router):
        origin = (38.5831, -90.4068)
        dest = (38.2527, -85.7585)
        result = router.get_route(origin, dest)
        assert result.origin == origin
        assert result.destination == dest


class TestHaversineDurationEstimate:
    """Tests for duration estimation (distance-derived)"""

    def test_duration_scales_with_speed(self):
        router_slow = HaversineRouter(avg_speed_mph=50.0)
        router_fast = HaversineRouter(avg_speed_mph=100.0)

        result_slow = router_slow.get_route((0, 0), (1, 1))
        result_fast = router_fast.get_route((0, 0), (1, 1))

        # Same distance, but fast router should take half the time
        assert abs(result_slow.duration_minutes - 2 * result_fast.duration_minutes) < 0.01

    def test_duration_formula(self):
        router = HaversineRouter(avg_speed_mph=60.0)
        result = router.get_route((0, 0), (1, 1))

        # duration_minutes = (distance_miles / speed_mph) * 60
        expected = (result.distance_miles / 60.0) * 60.0
        assert result.duration_minutes == expected


class TestHaversineDistanceMatrix:
    """Tests for distance matrix calculations"""

    @pytest.fixture
    def router(self):
        return HaversineRouter(avg_speed_mph=55.0)

    @pytest.fixture
    def sample_locations(self):
        return [
            (38.5831, -90.4068),   # Kirkwood, MO
            (38.2527, -85.7585),   # Louisville, KY
            (39.7392, -104.9903),  # Denver, CO
        ]

    def test_matrix_dimensions(self, router, sample_locations):
        result = router.get_distance_matrix(sample_locations, sample_locations)
        assert len(result.distances) == 3
        assert len(result.distances[0]) == 3
        assert len(result.durations) == 3
        assert len(result.durations[0]) == 3

    def test_matrix_diagonal_is_zero(self, router, sample_locations):
        result = router.get_distance_matrix(sample_locations, sample_locations)
        for i in range(3):
            assert result.distances[i][i] == 0.0
            assert result.durations[i][i] == 0.0

    def test_matrix_is_symmetric(self, router, sample_locations):
        result = router.get_distance_matrix(sample_locations, sample_locations)
        for i in range(3):
            for j in range(3):
                assert abs(result.distances[i][j] - result.distances[j][i]) < 0.01

    def test_matrix_api_calls_is_zero(self, router, sample_locations):
        result = router.get_distance_matrix(sample_locations, sample_locations)
        assert result.api_calls_made == 0

    def test_matrix_source_is_haversine(self, router, sample_locations):
        result = router.get_distance_matrix(sample_locations, sample_locations)
        assert result.source == DistanceSource.HAVERSINE

    def test_matrix_is_estimated_true(self, router, sample_locations):
        result = router.get_distance_matrix(sample_locations, sample_locations)
        assert result.is_estimated is True

    def test_get_distance_helper(self, router, sample_locations):
        result = router.get_distance_matrix(sample_locations, sample_locations)
        assert result.get_distance(0, 1) == result.distances[0][1]
        assert result.get_distance(1, 2) == result.distances[1][2]

    def test_get_duration_helper(self, router, sample_locations):
        result = router.get_distance_matrix(sample_locations, sample_locations)
        assert result.get_duration(0, 1) == result.durations[0][1]
        assert result.get_duration(1, 2) == result.durations[1][2]

    def test_asymmetric_matrix(self, router):
        origins = [(38.5831, -90.4068)]
        destinations = [(38.2527, -85.7585), (39.7392, -104.9903)]

        result = router.get_distance_matrix(origins, destinations)

        assert len(result.distances) == 1
        assert len(result.distances[0]) == 2
        assert len(result.origins) == 1
        assert len(result.destinations) == 2


class TestHaversineSymmetricMatrix:
    """Tests for symmetric matrix helper"""

    def test_symmetric_matrix_uses_same_origins_destinations(self):
        router = HaversineRouter()
        locations = [(0, 0), (1, 1), (2, 2)]

        result = router.get_symmetric_matrix(locations)

        assert result.origins == locations
        assert result.destinations == locations
