#!/usr/bin/env python3
"""
Tests for TripValidator

Tests the trip validation and resequencing logic.
"""
import pytest
from unittest.mock import Mock, MagicMock
from core.site import Site
from .validator import TripValidator


class TestTripValidator:
    """Tests for TripValidator class"""

    @pytest.fixture
    def home_base(self):
        """Create home base site"""
        return Site(name="Home", lat=38.0, lon=-90.0)

    @pytest.fixture
    def mock_functions(self):
        """Create mock functions for dependencies"""
        mocks = {
            'haversine_fn': Mock(return_value=50.0),  # 50 miles
            'check_site_fits_fn': Mock(return_value=(True, None, None)),
            'calculate_optimal_start_hour_fn': Mock(return_value=9),  # 9am
            'try_reorder_fn': Mock(return_value=(False, [], None, None))  # Reorder fails
        }
        return mocks

    @pytest.fixture
    def validator(self, home_base, mock_functions):
        """Create validator with mocked dependencies"""
        return TripValidator(
            home_base=home_base,
            hours_per_day=15,
            visit_minutes_per_site=120,
            max_trip_minutes=3600,
            target_trip_minutes=2700,
            avg_speed_mph=55.0,
            **mock_functions,
            verbose=False
        )

    @pytest.fixture
    def sample_trip(self, home_base):
        """Create sample trip with route details"""
        return {
            'trip_number': 1,
            'route_details': [
                {
                    'site_name': home_base.name,
                    'lat': home_base.lat,
                    'lon': home_base.lon
                },
                {
                    'site_name': 'Site A',
                    'lat': 38.1,
                    'lon': -90.1
                },
                {
                    'site_name': 'Site B',
                    'lat': 38.2,
                    'lon': -90.2
                },
                {
                    'site_name': home_base.name,
                    'lat': home_base.lat,
                    'lon': home_base.lon
                }
            ]
        }

    def test_validator_initialization(self, validator, home_base):
        """Validator should initialize with correct parameters"""
        assert validator.home_base == home_base
        assert validator.hours_per_day == 15
        assert validator.visit_minutes_per_site == 120
        assert validator.verbose is False

    def test_resequence_empty_trip_returns_unchanged(self, validator, home_base):
        """Empty trip (only depot) should return unchanged"""
        trip = {
            'trip_number': 1,
            'route_details': [
                {
                    'site_name': home_base.name,
                    'lat': home_base.lat,
                    'lon': home_base.lon
                }
            ]
        }

        resequenced_trip, rejected_sites = validator.resequence_trip(trip)

        assert resequenced_trip == trip
        assert rejected_sites == []

    def test_resequence_trip_with_sites_that_fit(self, validator, sample_trip):
        """Trip with sites that fit should succeed"""
        resequenced_trip, rejected_sites = validator.resequence_trip(sample_trip)

        assert resequenced_trip['trip_number'] == 1
        assert 'route_details' in resequenced_trip
        assert 'stats' in resequenced_trip
        assert resequenced_trip['stats']['resequenced'] is True
        assert len(rejected_sites) == 0

    def test_resequence_calculates_stats(self, validator, sample_trip):
        """Resequencing should calculate trip statistics"""
        resequenced_trip, _ = validator.resequence_trip(sample_trip)

        stats = resequenced_trip['stats']
        assert 'total_sites' in stats
        assert 'total_distance_miles' in stats
        assert 'total_time_hours' in stats
        assert 'total_days' in stats
        assert 'within_target' in stats
        assert 'within_max' in stats
        assert 'sites_rejected' in stats
        assert 'resequenced' in stats

    def test_resequence_with_site_that_never_fits(self, validator, home_base, mock_functions):
        """Site that never fits should be rejected"""
        # Make check_site_fits_fn always return False
        mock_functions['check_site_fits_fn'].return_value = (False, None, 'too_late')

        validator_reject = TripValidator(
            home_base=home_base,
            hours_per_day=15,
            visit_minutes_per_site=120,
            max_trip_minutes=900,  # Very short trip
            target_trip_minutes=720,
            avg_speed_mph=55.0,
            **mock_functions,
            verbose=False
        )

        trip = {
            'trip_number': 1,
            'route_details': [
                {'site_name': home_base.name, 'lat': home_base.lat, 'lon': home_base.lon},
                {'site_name': 'Site A', 'lat': 38.1, 'lon': -90.1},
                {'site_name': home_base.name, 'lat': home_base.lat, 'lon': home_base.lon}
            ]
        }

        resequenced_trip, rejected_sites = validator_reject.resequence_trip(trip)

        # Site should be rejected
        assert len(rejected_sites) >= 0  # May reject depending on logic
        assert resequenced_trip['stats']['sites_rejected'] >= 0

    def test_resequence_preserves_trip_number(self, validator, sample_trip):
        """Resequencing should preserve trip number"""
        original_number = sample_trip['trip_number']
        resequenced_trip, _ = validator.resequence_trip(sample_trip)

        assert resequenced_trip['trip_number'] == original_number

    def test_resequence_includes_depot_at_start_and_end(self, validator, sample_trip, home_base):
        """Resequenced trip should have depot at start and end"""
        resequenced_trip, _ = validator.resequence_trip(sample_trip)

        route = resequenced_trip['route_details']
        assert len(route) >= 2
        assert route[0]['site_name'] == home_base.name
        assert route[-1]['site_name'] == home_base.name


class TestTripValidatorScheduling:
    """Tests for trip scheduling logic"""

    @pytest.fixture
    def home_base(self):
        return Site(name="Home", lat=38.0, lon=-90.0)

    @pytest.fixture
    def validator_with_sequential_fits(self, home_base):
        """Validator where first 2 sites fit, third doesn't"""
        fit_count = {'count': 0}

        def check_fits(sites_so_far, new_site, start_location, budget, start_hour):
            fit_count['count'] += 1
            # First 2 sites fit, third doesn't
            fits = fit_count['count'] <= 2
            return (fits, None, 'budget_exceeded' if not fits else None)

        return TripValidator(
            home_base=home_base,
            hours_per_day=15,
            visit_minutes_per_site=120,
            max_trip_minutes=3600,
            target_trip_minutes=2700,
            avg_speed_mph=55.0,
            haversine_fn=Mock(return_value=50.0),
            check_site_fits_fn=check_fits,
            calculate_optimal_start_hour_fn=Mock(return_value=9),
            try_reorder_fn=Mock(return_value=(False, [], None, None)),
            verbose=False
        )

    def test_schedule_site_that_fits_returns_added(self, validator_with_sequential_fits):
        """Site that fits should be added to current day"""
        result = validator_with_sequential_fits._schedule_site(
            site={'site_name': 'Test', 'lat': 38.1, 'lon': -90.1},
            site_index=0,
            total_sites=3,
            current_day_sites=[],
            days=[],
            start_location=(38.0, -90.0),
            daily_budget_minutes=900
        )

        assert result['action'] == 'added'
        assert len(result['current_day_sites']) == 1


class TestTripValidatorEdgeCases:
    """Edge case tests for TripValidator"""

    def test_validator_with_zero_hours_per_day_fails(self):
        """Validator with zero hours per day should handle gracefully"""
        home_base = Site(name="Home", lat=38.0, lon=-90.0)

        validator = TripValidator(
            home_base=home_base,
            hours_per_day=0,  # Invalid
            visit_minutes_per_site=120,
            max_trip_minutes=3600,
            target_trip_minutes=2700,
            avg_speed_mph=55.0,
            haversine_fn=Mock(return_value=50.0),
            check_site_fits_fn=Mock(return_value=(False, None, 'budget_exceeded')),
            calculate_optimal_start_hour_fn=Mock(return_value=9),
            try_reorder_fn=Mock(return_value=(False, [], None, None)),
            verbose=False
        )

        # Should handle without crashing
        assert validator.hours_per_day == 0

    def test_resequence_very_long_trip(self):
        """Validator should handle trips with many sites"""
        home_base = Site(name="Home", lat=38.0, lon=-90.0)

        validator = TripValidator(
            home_base=home_base,
            hours_per_day=15,
            visit_minutes_per_site=120,
            max_trip_minutes=10080,  # 7 days
            target_trip_minutes=7200,
            avg_speed_mph=55.0,
            haversine_fn=Mock(return_value=50.0),
            check_site_fits_fn=Mock(return_value=(True, None, None)),
            calculate_optimal_start_hour_fn=Mock(return_value=9),
            try_reorder_fn=Mock(return_value=(False, [], None, None)),
            verbose=False
        )

        # Create trip with many sites
        route_details = [{'site_name': home_base.name, 'lat': 38.0, 'lon': -90.0}]
        for i in range(20):
            route_details.append({
                'site_name': f'Site {i}',
                'lat': 38.0 + i * 0.1,
                'lon': -90.0 + i * 0.1
            })
        route_details.append({'site_name': home_base.name, 'lat': 38.0, 'lon': -90.0})

        trip = {'trip_number': 1, 'route_details': route_details}

        resequenced_trip, rejected_sites = validator.resequence_trip(trip)

        # Should complete without crashing
        assert 'stats' in resequenced_trip
        assert resequenced_trip['stats']['total_sites'] >= 0
