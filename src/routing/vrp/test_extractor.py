#!/usr/bin/env python3
"""
Tests for TripExtractor

Tests the trip extraction and formatting logic with day-aware processing.
"""
import pytest
from unittest.mock import Mock, MagicMock
from core.site import Site
from .extractor import TripExtractor


class TestTripExtractor:
    """Tests for TripExtractor class"""

    @pytest.fixture
    def home_base(self):
        """Create home base site"""
        return Site(name="Home", lat=38.0, lon=-90.0)

    @pytest.fixture
    def sample_sites(self, home_base):
        """Create sample sites list"""
        return [
            home_base,
            Site(name="Site A", lat=38.1, lon=-90.1),
            Site(name="Site B", lat=38.2, lon=-90.2),
        ]

    @pytest.fixture
    def mock_functions(self):
        """Create mock functions for dependencies"""
        return {
            'haversine_fn': Mock(return_value=50.0),
            'calculate_optimal_start_hour_fn': Mock(return_value=9)
        }

    @pytest.fixture
    def extractor(self, sample_sites, home_base, mock_functions):
        """Create extractor with mocked dependencies"""
        return TripExtractor(
            sites=sample_sites,
            home_base=home_base,
            num_vehicles=2,
            hours_per_day=15,
            preferred_hours_per_day=12,
            visit_minutes_per_site=120,
            target_trip_minutes=2700,
            max_trip_minutes=3600,
            avg_speed_mph=55.0,
            earliest_start_hour=6,
            preferred_start_hour=9,
            **mock_functions,
            verbose=False
        )

    def test_extractor_initialization(self, extractor, home_base):
        """Extractor should initialize with correct parameters"""
        assert extractor.home_base == home_base
        assert extractor.num_vehicles == 2
        assert extractor.hours_per_day == 15
        assert extractor.preferred_hours_per_day == 12
        assert extractor.visit_minutes_per_site == 120
        assert extractor.verbose is False

    def test_parse_time_string_with_colon(self, extractor):
        """Should parse HH:MM format time string"""
        result = extractor._parse_time_string("14:30", default=0)
        assert result == 14 * 60 + 30

    def test_parse_time_string_returns_default_without_colon(self, extractor):
        """Should return default when no colon in string"""
        result = extractor._parse_time_string("invalid", default=540)
        assert result == 540

    def test_calculate_day_assignment_fits_in_current_day(self, extractor):
        """Site that fits in current day should stay in that day"""
        day_num, time_used, positioning = extractor._calculate_day_assignment(
            time_needed=200.0,
            current_day=1,
            current_day_time_used=300.0,
            daily_budget=900,
            travel_time=80.0,
            visit_time=120.0
        )

        assert day_num == 1
        assert time_used == 500.0  # 300 + 200
        assert positioning == 0

    def test_calculate_day_assignment_rolls_to_next_day(self, extractor):
        """Site that doesn't fit should roll to next day"""
        day_num, time_used, positioning = extractor._calculate_day_assignment(
            time_needed=200.0,
            current_day=1,
            current_day_time_used=800.0,
            daily_budget=900,
            travel_time=80.0,
            visit_time=120.0
        )

        assert day_num == 2
        assert positioning == 100.0  # 900 - 800
        # Remaining travel (0) + visit time
        assert time_used == 120.0

    def test_calculate_day_assignment_with_remaining_travel(self, extractor):
        """Site rollover should account for remaining travel time"""
        day_num, time_used, positioning = extractor._calculate_day_assignment(
            time_needed=300.0,  # travel 180 + visit 120
            current_day=1,
            current_day_time_used=700.0,
            daily_budget=900,
            travel_time=180.0,
            visit_time=120.0
        )

        assert day_num == 2
        assert positioning == 200.0  # 900 - 700
        # Remaining travel (180 - 200 = max(0, -20) = 0) + visit 120
        # Actually: remaining_travel = max(0, 180 - 200) = 0
        assert time_used == 120.0

    def test_create_stop_info_with_basic_site(self, extractor, sample_sites):
        """Should create stop info with correct fields"""
        site = sample_sites[1]  # Site A
        stop_info = extractor._create_stop_info(
            site=site,
            arrival_minutes=200,
            day_number=1,
            day_time_used=200.0
        )

        assert stop_info['site_name'] == 'Site A'
        assert stop_info['lat'] == 38.1
        assert stop_info['lon'] == -90.1
        assert stop_info['arrival_minutes'] == 200
        assert stop_info['day'] == 1
        assert 'time_of_day' in stop_info

    def test_create_stop_info_calculates_time_of_day(self, extractor, sample_sites):
        """Should calculate time_of_day correctly"""
        site = sample_sites[1]
        # day_time_used = 200 min, visit = 120 min
        # arrival_time_in_day = 200 - 120 = 80 min into day
        # earliest_start = 6:00 (360 min)
        # actual_minutes = 360 + 80 = 440 min = 7:20
        stop_info = extractor._create_stop_info(
            site=site,
            arrival_minutes=200,
            day_number=1,
            day_time_used=200.0
        )

        assert stop_info['time_of_day'] == "07:20"

    def test_create_depot_stop(self, extractor, home_base):
        """Should create depot stop with home base info"""
        depot_stop = extractor._create_depot_stop(
            site=home_base,
            arrival_minutes=0,
            current_day=1,
            current_day_time_used=0
        )

        assert depot_stop['site_name'] == 'Home'
        assert depot_stop['lat'] == 38.0
        assert depot_stop['lon'] == -90.0
        assert depot_stop['day'] == 1
        assert depot_stop['time_of_day'] == "06:00"  # earliest_start_hour

    def test_mark_positioning_on_non_depot_stop(self, extractor):
        """Should mark positioning info on non-depot stop"""
        previous_stop = {'site_name': 'Site A'}
        extractor._mark_positioning(
            previous_stop=previous_stop,
            positioning_time=60.0,
            toward_site='Site B',
            next_day=2
        )

        assert 'end_of_day_positioning' in previous_stop
        pos = previous_stop['end_of_day_positioning']
        assert pos['positioning_minutes'] == 60.0
        assert pos['toward_site'] == 'Site B'
        assert pos['next_day_starts'] == 2

    def test_mark_positioning_skips_depot(self, extractor, home_base):
        """Should not mark positioning on depot stop"""
        depot_stop = {'site_name': home_base.name}
        extractor._mark_positioning(
            previous_stop=depot_stop,
            positioning_time=60.0,
            toward_site='Site A',
            next_day=2
        )

        assert 'end_of_day_positioning' not in depot_stop


class TestTripExtractorOperatingHours:
    """Tests for operating hours checking"""

    @pytest.fixture
    def extractor(self):
        """Create basic extractor"""
        home_base = Site(name="Home", lat=38.0, lon=-90.0)
        sites = [home_base]
        return TripExtractor(
            sites=sites,
            home_base=home_base,
            num_vehicles=1,
            hours_per_day=15,
            preferred_hours_per_day=12,
            visit_minutes_per_site=120,
            target_trip_minutes=2700,
            max_trip_minutes=3600,
            avg_speed_mph=55.0,
            earliest_start_hour=6,
            preferred_start_hour=9,
            haversine_fn=Mock(return_value=50.0),
            calculate_optimal_start_hour_fn=Mock(return_value=9),
            verbose=False
        )

    def test_check_operating_hours_no_hours_on_site(self, extractor):
        """Site without operating hours should not add annotations"""
        site = Site(name="Test", lat=38.0, lon=-90.0)
        stop_info = {'site_name': 'Test', 'time_of_day': '10:00'}

        extractor._check_operating_hours(stop_info, site)

        assert 'operating_hours' not in stop_info
        assert 'time_constraint_warning' not in stop_info

    def test_check_operating_hours_within_hours(self, extractor):
        """Arrival within operating hours should pass"""
        site = Site(name="Test", lat=38.0, lon=-90.0)
        site.operating_hours = type('obj', (object,), {
            'opens': 8 * 60,
            'closes': 17 * 60
        })()
        stop_info = {'site_name': 'Test', 'time_of_day': '10:00'}

        extractor._check_operating_hours(stop_info, site)

        assert 'operating_hours' in stop_info
        assert 'time_constraint_warning' not in stop_info

    def test_check_operating_hours_after_closing(self, extractor):
        """Arrival after closing should create violation warning"""
        site = Site(name="Test", lat=38.0, lon=-90.0)
        site.operating_hours = type('obj', (object,), {
            'opens': 8 * 60,
            'closes': 17 * 60
        })()
        site.always_stamp_available = False
        stop_info = {'site_name': 'Test', 'time_of_day': '18:00'}

        extractor._check_operating_hours(stop_info, site)

        assert 'time_constraint_warning' in stop_info
        assert 'VIOLATION' in stop_info['time_constraint_warning']
        assert stop_info.get('invalid_visit') is True

    def test_check_operating_hours_after_closing_with_always_available(self, extractor):
        """Arrival after closing at always-available site should be INFO only"""
        site = Site(name="Test", lat=38.0, lon=-90.0)
        site.operating_hours = type('obj', (object,), {
            'opens': 8 * 60,
            'closes': 17 * 60
        })()
        site.always_stamp_available = True
        stop_info = {'site_name': 'Test', 'time_of_day': '18:00'}

        extractor._check_operating_hours(stop_info, site)

        assert 'time_constraint_warning' in stop_info
        assert 'INFO' in stop_info['time_constraint_warning']
        assert 'invalid_visit' not in stop_info

    def test_check_operating_hours_before_opening(self, extractor):
        """Arrival before opening should create info message"""
        site = Site(name="Test", lat=38.0, lon=-90.0)
        site.operating_hours = type('obj', (object,), {
            'opens': 8 * 60,
            'closes': 17 * 60
        })()
        stop_info = {'site_name': 'Test', 'time_of_day': '07:00'}

        extractor._check_operating_hours(stop_info, site)

        assert 'time_constraint_info' in stop_info
        assert 'Early arrival' in stop_info['time_constraint_info']


class TestTripExtractorEdgeCases:
    """Edge case tests for TripExtractor"""

    def test_extractor_with_multiple_vehicles(self):
        """Extractor should handle multiple vehicles"""
        home_base = Site(name="Home", lat=38.0, lon=-90.0)
        sites = [home_base]
        extractor = TripExtractor(
            sites=sites,
            home_base=home_base,
            num_vehicles=5,
            hours_per_day=15,
            preferred_hours_per_day=12,
            visit_minutes_per_site=120,
            target_trip_minutes=2700,
            max_trip_minutes=3600,
            avg_speed_mph=55.0,
            earliest_start_hour=6,
            preferred_start_hour=9,
            haversine_fn=Mock(return_value=50.0),
            calculate_optimal_start_hour_fn=Mock(return_value=9),
            verbose=False
        )

        assert extractor.num_vehicles == 5

    def test_parse_time_string_edge_cases(self):
        """Parse time string should handle edge cases"""
        home_base = Site(name="Home", lat=38.0, lon=-90.0)
        extractor = TripExtractor(
            sites=[home_base],
            home_base=home_base,
            num_vehicles=1,
            hours_per_day=15,
            preferred_hours_per_day=12,
            visit_minutes_per_site=120,
            target_trip_minutes=2700,
            max_trip_minutes=3600,
            avg_speed_mph=55.0,
            earliest_start_hour=6,
            preferred_start_hour=9,
            haversine_fn=Mock(return_value=50.0),
            calculate_optimal_start_hour_fn=Mock(return_value=9),
            verbose=False
        )

        # Midnight
        assert extractor._parse_time_string("00:00", 0) == 0
        # Just before midnight
        assert extractor._parse_time_string("23:59", 0) == 23 * 60 + 59
        # Noon
        assert extractor._parse_time_string("12:00", 0) == 12 * 60
