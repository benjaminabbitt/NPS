"""Tests for geo_utils module."""
import pytest
from geo_utils import (
    haversine_distance,
    travel_time_minutes,
    distance_matrix,
    EARTH_RADIUS_MILES,
)


class TestHaversineDistance:
    """Tests for haversine_distance function."""

    def test_same_point_returns_zero(self):
        dist = haversine_distance(38.5831, -90.4068, 38.5831, -90.4068)
        assert dist == 0.0

    def test_kirkwood_to_gateway_arch(self):
        """Known distance: Kirkwood to Gateway Arch ~12 miles"""
        dist = haversine_distance(
            38.5831, -90.4068,  # Kirkwood
            38.6247, -90.1848   # Gateway Arch
        )
        assert 10 < dist < 15

    def test_new_york_to_los_angeles(self):
        """Known distance: NYC to LA ~2,450 miles"""
        dist = haversine_distance(
            40.7128, -74.0060,  # NYC
            34.0522, -118.2437  # LA
        )
        assert 2400 < dist < 2500

    def test_distance_is_symmetric(self):
        dist1 = haversine_distance(38.5831, -90.4068, 37.1870, -86.1008)
        dist2 = haversine_distance(37.1870, -86.1008, 38.5831, -90.4068)
        assert dist1 == dist2

    def test_invalid_latitude_raises_error(self):
        with pytest.raises(ValueError, match="Invalid latitude"):
            haversine_distance(91, 0, 0, 0)

    def test_invalid_longitude_raises_error(self):
        with pytest.raises(ValueError, match="Invalid longitude"):
            haversine_distance(0, 181, 0, 0)

    def test_earth_radius_constant(self):
        """Verify Earth radius is in miles (not km)"""
        assert EARTH_RADIUS_MILES == 3959


class TestTravelTimeMinutes:
    """Tests for travel_time_minutes function."""

    def test_same_point_returns_zero(self):
        time = travel_time_minutes(38.5831, -90.4068, 38.5831, -90.4068)
        assert time == 0.0

    def test_55mph_default_speed(self):
        """At 55 mph, 55 miles takes 60 minutes"""
        # Find a ~55 mile distance
        dist = haversine_distance(38.5831, -90.4068, 37.5504, -89.7346)
        time = travel_time_minutes(38.5831, -90.4068, 37.5504, -89.7346)
        expected = (dist / 55.0) * 60.0
        assert abs(time - expected) < 0.01

    def test_custom_speed(self):
        dist = haversine_distance(38.5831, -90.4068, 38.6247, -90.1848)
        time_30mph = travel_time_minutes(38.5831, -90.4068, 38.6247, -90.1848, 30.0)
        time_60mph = travel_time_minutes(38.5831, -90.4068, 38.6247, -90.1848, 60.0)
        # 30 mph should take twice as long as 60 mph
        assert abs(time_30mph - 2 * time_60mph) < 0.01

    def test_zero_speed_raises_error(self):
        with pytest.raises(ValueError, match="must be positive"):
            travel_time_minutes(38.0, -90.0, 39.0, -91.0, 0.0)

    def test_negative_speed_raises_error(self):
        with pytest.raises(ValueError, match="must be positive"):
            travel_time_minutes(38.0, -90.0, 39.0, -91.0, -55.0)


class TestDistanceMatrix:
    """Tests for distance_matrix function."""

    def test_empty_list(self):
        matrix = distance_matrix([])
        assert matrix == []

    def test_single_location(self):
        matrix = distance_matrix([(38.5831, -90.4068)])
        assert matrix == [[0.0]]

    def test_two_locations_symmetric(self):
        locations = [(38.5831, -90.4068), (38.6247, -90.1848)]
        matrix = distance_matrix(locations)

        assert len(matrix) == 2
        assert matrix[0][0] == 0.0
        assert matrix[1][1] == 0.0
        assert matrix[0][1] == matrix[1][0]  # Symmetric
        assert matrix[0][1] > 0

    def test_three_locations(self):
        locations = [
            (38.5831, -90.4068),  # Kirkwood
            (38.6247, -90.1848),  # Gateway Arch
            (37.1870, -86.1008),  # Mammoth Cave
        ]
        matrix = distance_matrix(locations)

        assert len(matrix) == 3
        assert all(len(row) == 3 for row in matrix)
        # Diagonal is zero
        assert matrix[0][0] == 0.0
        assert matrix[1][1] == 0.0
        assert matrix[2][2] == 0.0
        # Symmetric
        assert matrix[0][1] == matrix[1][0]
        assert matrix[0][2] == matrix[2][0]
        assert matrix[1][2] == matrix[2][1]

    def test_in_meters_conversion(self):
        locations = [(38.5831, -90.4068), (38.6247, -90.1848)]
        matrix_miles = distance_matrix(locations, in_meters=False)
        matrix_meters = distance_matrix(locations, in_meters=True)

        # Meters should be ~1609 times miles
        ratio = matrix_meters[0][1] / matrix_miles[0][1]
        assert 1608 < ratio < 1610
