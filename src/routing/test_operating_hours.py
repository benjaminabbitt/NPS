"""Tests for operating_hours module."""
import pytest
from operating_hours import (
    ParsedHours,
    parse_operating_hours,
    parse_time_string,
    check_operating_hours_violation,
    DEFAULT_OPENS_MINUTES,
    DEFAULT_CLOSES_MINUTES,
)


class TestParsedHours:
    """Tests for ParsedHours dataclass."""

    def test_create_parsed_hours(self):
        hours = ParsedHours(opens=540, closes=1020)  # 9 AM - 5 PM
        assert hours.opens == 540
        assert hours.closes == 1020

    def test_opens_hour_property(self):
        hours = ParsedHours(opens=540, closes=1020)
        assert hours.opens_hour == 9.0

    def test_closes_hour_property(self):
        hours = ParsedHours(opens=540, closes=1020)
        assert hours.closes_hour == 17.0

    def test_is_open_at_during_hours(self):
        hours = ParsedHours(opens=540, closes=1020)  # 9 AM - 5 PM
        assert hours.is_open_at(600) is True  # 10 AM
        assert hours.is_open_at(540) is True  # Exactly opening
        assert hours.is_open_at(1020) is True  # Exactly closing

    def test_is_open_at_outside_hours(self):
        hours = ParsedHours(opens=540, closes=1020)  # 9 AM - 5 PM
        assert hours.is_open_at(400) is False  # Before opening
        assert hours.is_open_at(1100) is False  # After closing

    def test_format_time_range(self):
        hours = ParsedHours(opens=540, closes=1020)
        assert hours.format_time_range() == "9 AM - 5 PM"

    def test_format_time_range_with_minutes(self):
        hours = ParsedHours(opens=570, closes=1050)  # 9:30 AM - 5:30 PM
        assert hours.format_time_range() == "9:30 AM - 5:30 PM"


class TestParseTimeString:
    """Tests for parse_time_string function."""

    def test_parse_12_hour_am(self):
        assert parse_time_string("9:00 AM") == 540
        assert parse_time_string("9:30 AM") == 570

    def test_parse_12_hour_pm(self):
        assert parse_time_string("5:00 PM") == 1020
        assert parse_time_string("5:30 PM") == 1050

    def test_parse_noon(self):
        assert parse_time_string("12:00 PM") == 720

    def test_parse_midnight(self):
        assert parse_time_string("12:00 AM") == 0

    def test_parse_24_hour_format(self):
        assert parse_time_string("09:00") == 540
        assert parse_time_string("17:00") == 1020
        assert parse_time_string("00:00") == 0
        assert parse_time_string("23:59") == 1439

    def test_parse_lowercase(self):
        assert parse_time_string("9:00 am") == 540
        assert parse_time_string("5:00 pm") == 1020

    def test_parse_without_colon(self):
        assert parse_time_string("9 AM") == 540
        assert parse_time_string("5 PM") == 1020

    def test_parse_empty_returns_none(self):
        assert parse_time_string("") is None
        assert parse_time_string(None) is None

    def test_parse_invalid_returns_none(self):
        assert parse_time_string("invalid") is None
        assert parse_time_string("25:00") is None


class TestParseOperatingHours:
    """Tests for parse_operating_hours function."""

    def test_parse_none_returns_defaults(self):
        hours = parse_operating_hours(None)
        assert hours.opens == DEFAULT_OPENS_MINUTES
        assert hours.closes == DEFAULT_CLOSES_MINUTES

    def test_parse_dict_with_int_minutes(self):
        hours = parse_operating_hours({'opens': 540, 'closes': 1020})
        assert hours.opens == 540
        assert hours.closes == 1020

    def test_parse_dict_with_string_times(self):
        hours = parse_operating_hours({'opens': '9:00 AM', 'closes': '5:00 PM'})
        assert hours.opens == 540
        assert hours.closes == 1020

    def test_parse_dict_mixed_formats(self):
        hours = parse_operating_hours({'opens': 540, 'closes': '5:00 PM'})
        assert hours.opens == 540
        assert hours.closes == 1020

    def test_parse_partial_dict_uses_defaults(self):
        hours = parse_operating_hours({'opens': 540})
        assert hours.opens == 540
        assert hours.closes == DEFAULT_CLOSES_MINUTES

    def test_parse_parsed_hours_passthrough(self):
        original = ParsedHours(opens=600, closes=900)
        result = parse_operating_hours(original)
        assert result is original

    def test_parse_invalid_type_returns_defaults(self):
        hours = parse_operating_hours("not a dict")
        assert hours.opens == DEFAULT_OPENS_MINUTES
        assert hours.closes == DEFAULT_CLOSES_MINUTES


class TestCheckOperatingHoursViolation:
    """Tests for check_operating_hours_violation function."""

    def test_no_violation_during_hours(self):
        hours = ParsedHours(opens=540, closes=1020)
        assert check_operating_hours_violation(600, hours) is False

    def test_violation_before_opening(self):
        hours = ParsedHours(opens=540, closes=1020)
        assert check_operating_hours_violation(400, hours) is True

    def test_violation_after_closing(self):
        hours = ParsedHours(opens=540, closes=1020)
        assert check_operating_hours_violation(1100, hours) is True

    def test_always_available_no_violation(self):
        hours = ParsedHours(opens=540, closes=1020)
        # Arrived before opening, but always available
        assert check_operating_hours_violation(400, hours, always_available=True) is False

    def test_none_hours_uses_defaults(self):
        # Default is 8 AM - 5 PM (480 - 1020)
        assert check_operating_hours_violation(500, None) is False  # 8:20 AM
        assert check_operating_hours_violation(400, None) is True   # Before 8 AM
