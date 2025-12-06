#!/usr/bin/env python3
"""
Tests for parser implementations
"""
import pytest
from .parsers import (
    RegexDurationParser,
    RegexOperatingHoursParser,
    MistuneMarkdownParser
)
from .types import OperatingHours


class TestRegexDurationParser:
    """Tests for RegexDurationParser"""

    @pytest.fixture
    def parser(self):
        return RegexDurationParser()

    def test_parse_single_hour(self, parser):
        """Should parse single hour values"""
        assert parser.parse("4 hours") == 4.0
        assert parser.parse("1 hour") == 1.0

    def test_parse_hour_range(self, parser):
        """Should parse hour ranges as average"""
        assert parser.parse("2-3 hours") == 2.5
        assert parser.parse("1-2 hours") == 1.5

    def test_parse_decimal_hours(self, parser):
        """Should parse decimal hours"""
        assert parser.parse("1.5 hours") == 1.5
        assert parser.parse("2.75 hours") == 2.75

    def test_parse_minutes(self, parser):
        """Should parse minutes to hours"""
        assert parser.parse("30 minutes") == 0.5
        assert parser.parse("45 min") == 0.75

    def test_parse_invalid_returns_zero(self, parser):
        """Should return 0 for invalid strings"""
        assert parser.parse("invalid") == 0.0
        assert parser.parse("") == 0.0


class TestRegexOperatingHoursParser:
    """Tests for RegexOperatingHoursParser"""

    @pytest.fixture
    def parser(self):
        return RegexOperatingHoursParser()

    def test_parse_standard_hours(self, parser):
        """Should parse standard hour format"""
        result = parser.parse("9:00 AM - 5:00 PM")
        assert result is not None
        assert result.opens == 540  # 9:00 AM
        assert result.closes == 1020  # 5:00 PM

    def test_parse_with_daily_prefix(self, parser):
        """Should handle 'Daily' prefix"""
        result = parser.parse("Daily 8:00 AM - 6:00 PM")
        assert result is not None
        assert result.opens == 480  # 8:00 AM
        assert result.closes == 1080  # 6:00 PM

    def test_parse_noon_and_midnight(self, parser):
        """Should handle 12:00 PM and 12:00 AM"""
        result = parser.parse("12:00 PM - 12:00 AM")
        assert result is not None
        assert result.opens == 720  # 12:00 PM (noon)
        assert result.closes == 0  # 12:00 AM (midnight)

    def test_parse_invalid_returns_none(self, parser):
        """Should return None for invalid strings"""
        assert parser.parse("invalid") is None
        assert parser.parse("") is None


class TestMistuneMarkdownParser:
    """Tests for MistuneMarkdownParser"""

    @pytest.fixture
    def parser(self):
        return MistuneMarkdownParser()

    def test_parse_simple_sections(self, parser):
        """Should parse markdown into sections"""
        content = """
## Section One
- Item 1
- Item 2

## Section Two
- Item A
- Item B
"""
        sections = parser.parse(content)
        assert 'Section One' in sections
        assert 'Section Two' in sections
        assert len(sections['Section One']) == 2
        assert len(sections['Section Two']) == 2

    def test_parse_empty_content(self, parser):
        """Should handle empty content"""
        sections = parser.parse("")
        assert sections == {}

    def test_parse_no_lists(self, parser):
        """Should handle content without lists"""
        content = """
## Heading
Just some text.
"""
        sections = parser.parse(content)
        # Should have the section but no items
        assert sections == {}
