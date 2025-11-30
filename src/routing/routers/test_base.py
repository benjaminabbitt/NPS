"""Tests for base router classes: RouteResult, DistanceMatrixResult, DistanceSource"""
import pytest
from .base import RouteResult, DistanceMatrixResult, DistanceSource


class TestDistanceSource:
    """Tests for DistanceSource enum"""

    def test_haversine_value(self):
        assert DistanceSource.HAVERSINE.value == "haversine"

    def test_osrm_value(self):
        assert DistanceSource.OSRM.value == "osrm"

    def test_google_maps_value(self):
        assert DistanceSource.GOOGLE_MAPS.value == "google"

    def test_cache_value(self):
        assert DistanceSource.CACHE.value == "cache"


class TestRouteResult:
    """Tests for RouteResult dataclass"""

    @pytest.fixture
    def sample_route(self):
        return RouteResult(
            origin=(38.5831, -90.4068),
            destination=(37.5504, -85.7346),
            distance_miles=250.5,
            duration_minutes=273.0,
            source=DistanceSource.HAVERSINE,
            is_estimated=True
        )

    def test_create_route_result(self, sample_route):
        assert sample_route.origin == (38.5831, -90.4068)
        assert sample_route.destination == (37.5504, -85.7346)
        assert sample_route.distance_miles == 250.5
        assert sample_route.duration_minutes == 273.0
        assert sample_route.source == DistanceSource.HAVERSINE
        assert sample_route.is_estimated is True

    def test_duration_hours_property(self, sample_route):
        assert sample_route.duration_hours == 273.0 / 60.0
        assert sample_route.duration_hours == 4.55

    def test_duration_hours_zero(self):
        route = RouteResult(
            origin=(0, 0),
            destination=(0, 0),
            distance_miles=0,
            duration_minutes=0,
            source=DistanceSource.HAVERSINE,
            is_estimated=True
        )
        assert route.duration_hours == 0.0

    def test_is_estimated_false_for_osrm(self):
        route = RouteResult(
            origin=(38.5831, -90.4068),
            destination=(37.5504, -85.7346),
            distance_miles=280.0,
            duration_minutes=300.0,
            source=DistanceSource.OSRM,
            is_estimated=False
        )
        assert route.is_estimated is False
        assert route.source == DistanceSource.OSRM


class TestDistanceMatrixResult:
    """Tests for DistanceMatrixResult dataclass"""

    @pytest.fixture
    def sample_matrix(self):
        origins = [(38.5831, -90.4068), (37.5504, -85.7346)]
        destinations = [(39.7392, -104.9903), (34.0522, -118.2437)]
        distances = [
            [850.0, 1850.0],  # From origin 0 to each destination
            [900.0, 1900.0],  # From origin 1 to each destination
        ]
        durations = [
            [927.3, 2018.2],
            [981.8, 2072.7],
        ]
        return DistanceMatrixResult(
            origins=origins,
            destinations=destinations,
            distances=distances,
            durations=durations,
            source=DistanceSource.HAVERSINE,
            is_estimated=True,
            api_calls_made=0
        )

    def test_create_matrix_result(self, sample_matrix):
        assert len(sample_matrix.origins) == 2
        assert len(sample_matrix.destinations) == 2
        assert len(sample_matrix.distances) == 2
        assert len(sample_matrix.distances[0]) == 2
        assert sample_matrix.source == DistanceSource.HAVERSINE
        assert sample_matrix.is_estimated is True
        assert sample_matrix.api_calls_made == 0

    def test_get_distance(self, sample_matrix):
        assert sample_matrix.get_distance(0, 0) == 850.0
        assert sample_matrix.get_distance(0, 1) == 1850.0
        assert sample_matrix.get_distance(1, 0) == 900.0
        assert sample_matrix.get_distance(1, 1) == 1900.0

    def test_get_duration(self, sample_matrix):
        assert sample_matrix.get_duration(0, 0) == 927.3
        assert sample_matrix.get_duration(0, 1) == 2018.2
        assert sample_matrix.get_duration(1, 0) == 981.8
        assert sample_matrix.get_duration(1, 1) == 2072.7

    def test_api_calls_made_default(self):
        matrix = DistanceMatrixResult(
            origins=[(0, 0)],
            destinations=[(1, 1)],
            distances=[[100.0]],
            durations=[[109.1]],
            source=DistanceSource.HAVERSINE,
            is_estimated=True
        )
        assert matrix.api_calls_made == 0

    def test_api_calls_made_tracked(self):
        matrix = DistanceMatrixResult(
            origins=[(0, 0)],
            destinations=[(1, 1)],
            distances=[[100.0]],
            durations=[[109.1]],
            source=DistanceSource.OSRM,
            is_estimated=False,
            api_calls_made=5
        )
        assert matrix.api_calls_made == 5
