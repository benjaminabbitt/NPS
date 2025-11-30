"""Tests for NPS site data model."""
import pytest
from pathlib import Path

from nps_site.site_model import (
    Activity,
    CancellationStamp,
    SiteData,
    VisitationSite,
    parse_duration,
    parse_user_data,
    STAMP_COLLECTION_MINUTES,
)


class TestParseDuration:
    """Tests for duration parsing from activity strings."""

    def test_parse_duration_single_minutes(self):
        """Parse '30 minutes' format."""
        assert parse_duration("30 minutes") == 30

    def test_parse_duration_range_minutes(self):
        """Parse '30-60 minutes' format - use average."""
        assert parse_duration("30-60 minutes") == 45

    def test_parse_duration_single_hours(self):
        """Parse '1 hour' format."""
        assert parse_duration("1 hour") == 60

    def test_parse_duration_range_hours(self):
        """Parse '1-1.5 hours' format - use average."""
        assert parse_duration("1-1.5 hours") == 75

    def test_parse_duration_mixed_hours_minutes(self):
        """Parse '1.5 hours' format."""
        assert parse_duration("1.5 hours") == 90

    def test_parse_duration_complex_with_extra_text(self):
        """Parse duration with additional text like '30-45 minutes, or 2.5-3 hours with trail'."""
        # Hours regex matches first (2.5-3 hours), so returns average of 2.5-3 hours = 165 min
        assert parse_duration("30-45 minutes, or 2.5-3 hours with trail") == 165

    def test_parse_duration_no_duration_returns_zero(self):
        """Return 0 if no duration found."""
        assert parse_duration("Some activity without time") == 0

    def test_parse_duration_hour_tour_format(self):
        """Parse '1 hour tour' format."""
        assert parse_duration("1 hour tour") == 60


class TestActivity:
    """Tests for Activity dataclass."""

    def test_activity_creation(self):
        """Create an Activity with all fields."""
        activity = Activity(
            name="Visit Memorial",
            duration_minutes=45,
            selected=False,
            reference_id="abc123",
        )
        assert activity.name == "Visit Memorial"
        assert activity.duration_minutes == 45
        assert activity.selected is False
        assert activity.reference_id == "abc123"

    def test_activity_default_selected_false(self):
        """Activity selected defaults to False."""
        activity = Activity(name="Test", duration_minutes=30)
        assert activity.selected is False

    def test_activity_from_markdown_unchecked(self):
        """Parse unchecked markdown activity line."""
        line = "- [ ] Visit the Memorial Building (30-60 minutes) [df93e6]"
        activity = Activity.from_markdown(line)
        assert activity.name == "Visit the Memorial Building"
        assert activity.duration_minutes == 45  # average of 30-60
        assert activity.selected is False
        assert activity.reference_id == "df93e6"

    def test_activity_from_markdown_checked(self):
        """Parse checked markdown activity line."""
        line = "- [x] Hike the Trail (1-1.5 hours) [abc123]"
        activity = Activity.from_markdown(line)
        assert activity.name == "Hike the Trail"
        assert activity.duration_minutes == 75  # average of 1-1.5 hours
        assert activity.selected is True
        assert activity.reference_id == "abc123"


class TestCancellationStamp:
    """Tests for CancellationStamp dataclass."""

    def test_stamp_creation(self):
        """Create a CancellationStamp with all fields."""
        stamp = CancellationStamp(
            location="Visitor Center",
            address="123 Main St",
            selected=True,
            reference_id="stamp1",
        )
        assert stamp.location == "Visitor Center"
        assert stamp.address == "123 Main St"
        assert stamp.selected is True

    def test_stamp_from_markdown_unchecked(self):
        """Parse unchecked stamp line."""
        line = "- [ ] Visitor Center (123 Main St, City, ST 12345) [abc123]"
        stamp = CancellationStamp.from_markdown(line)
        assert stamp.location == "Visitor Center"
        assert stamp.address == "123 Main St, City, ST 12345"
        assert stamp.selected is False
        assert stamp.reference_id == "abc123"

    def test_stamp_from_markdown_checked(self):
        """Parse checked stamp line."""
        line = "- [x] Birthplace Visitor Center (2995 Lincoln Farm Road, Hodgenville, KY 42748) [55afff]"
        stamp = CancellationStamp.from_markdown(line)
        assert stamp.location == "Birthplace Visitor Center"
        assert stamp.address == "2995 Lincoln Farm Road, Hodgenville, KY 42748"
        assert stamp.selected is True
        assert stamp.reference_id == "55afff"

    def test_stamp_from_markdown_with_seasonal_note(self):
        """Parse stamp line with additional notes."""
        line = "- [ ] Knob Creek Tavern (7120 Bardstown Road) - Seasonal [451bed]"
        stamp = CancellationStamp.from_markdown(line)
        assert stamp.location == "Knob Creek Tavern"
        assert "7120 Bardstown Road" in stamp.address
        assert stamp.selected is False


class TestSiteData:
    """Tests for SiteData model."""

    def test_site_data_creation(self):
        """Create SiteData with all fields."""
        site = SiteData(
            name="Test Site NHP",
            visited=False,
            cancellation_stamps=[],
            key_activities=[],
            hidden_gems=[],
            also_nearby=[],
        )
        assert site.name == "Test Site NHP"
        assert site.visited is False

    def test_stamp_collection_constant(self):
        """Stamp collection time is always 15 minutes."""
        assert STAMP_COLLECTION_MINUTES == 15

    def test_calculate_duration_no_selections(self):
        """Duration is 0 when nothing selected."""
        site = SiteData(
            name="Test",
            visited=False,
            cancellation_stamps=[],
            key_activities=[],
            hidden_gems=[],
            also_nearby=[],
        )
        assert site.calculate_selected_duration() == 0

    def test_calculate_duration_with_stamp_selected(self):
        """Any stamp selected adds 15 minutes flat."""
        stamp = CancellationStamp(
            location="VC", address="123 Main", selected=True, reference_id="a"
        )
        site = SiteData(
            name="Test",
            visited=False,
            cancellation_stamps=[stamp],
            key_activities=[],
            hidden_gems=[],
            also_nearby=[],
        )
        assert site.calculate_selected_duration() == 15

    def test_calculate_duration_multiple_stamps_still_15(self):
        """Multiple stamps selected still only 15 minutes total."""
        stamps = [
            CancellationStamp(location="VC1", address="a", selected=True, reference_id="1"),
            CancellationStamp(location="VC2", address="b", selected=True, reference_id="2"),
        ]
        site = SiteData(
            name="Test",
            visited=False,
            cancellation_stamps=stamps,
            key_activities=[],
            hidden_gems=[],
            also_nearby=[],
        )
        assert site.calculate_selected_duration() == 15

    def test_calculate_duration_with_activities(self):
        """Sum durations of selected activities."""
        activities = [
            Activity(name="A1", duration_minutes=30, selected=True),
            Activity(name="A2", duration_minutes=45, selected=False),
            Activity(name="A3", duration_minutes=60, selected=True),
        ]
        site = SiteData(
            name="Test",
            visited=False,
            cancellation_stamps=[],
            key_activities=activities,
            hidden_gems=[],
            also_nearby=[],
        )
        # 30 + 60 = 90 (A2 not selected)
        assert site.calculate_selected_duration() == 90

    def test_calculate_duration_stamps_plus_activities(self):
        """Stamps (15 min) plus activity durations."""
        stamp = CancellationStamp(location="VC", address="a", selected=True, reference_id="x")
        activity = Activity(name="A1", duration_minutes=30, selected=True)
        site = SiteData(
            name="Test",
            visited=False,
            cancellation_stamps=[stamp],
            key_activities=[activity],
            hidden_gems=[],
            also_nearby=[],
        )
        # 15 (stamp) + 30 (activity) = 45
        assert site.calculate_selected_duration() == 45

    def test_calculate_duration_includes_hidden_gems(self):
        """Hidden gems durations also included."""
        gem = Activity(name="Gem", duration_minutes=20, selected=True)
        site = SiteData(
            name="Test",
            visited=False,
            cancellation_stamps=[],
            key_activities=[],
            hidden_gems=[gem],
            also_nearby=[],
        )
        assert site.calculate_selected_duration() == 20

    def test_calculate_duration_includes_nearby(self):
        """Also Nearby durations included."""
        nearby = Activity(name="Nearby", duration_minutes=60, selected=True)
        site = SiteData(
            name="Test",
            visited=False,
            cancellation_stamps=[],
            key_activities=[],
            hidden_gems=[],
            also_nearby=[nearby],
        )
        assert site.calculate_selected_duration() == 60

    def test_calculate_duration_all_categories(self):
        """Sum all categories correctly."""
        stamp = CancellationStamp(location="VC", address="a", selected=True, reference_id="s")
        key = Activity(name="Key", duration_minutes=30, selected=True)
        gem = Activity(name="Gem", duration_minutes=20, selected=True)
        nearby = Activity(name="Near", duration_minutes=45, selected=True)
        site = SiteData(
            name="Test",
            visited=False,
            cancellation_stamps=[stamp],
            key_activities=[key],
            hidden_gems=[gem],
            also_nearby=[nearby],
        )
        # 15 + 30 + 20 + 45 = 110
        assert site.calculate_selected_duration() == 110


class TestParseUserData:
    """Tests for parsing user-data.md files."""

    def test_parse_user_data_from_string(self):
        """Parse a complete user-data.md content string."""
        content = """# Test Site NHP

[View Full Research Report](Test%20Site%20NHP.md)

- [ ] Visited

## Cancellation Stamps

- [x] Visitor Center (123 Main St, City, ST 12345) [abc123]

## Key Activities

- [x] Visit Memorial (30-60 minutes) [def456]
- [ ] Watch Film (20 minutes) [ghi789]

## Hidden Gems

- [ ] Secret Trail (1 hour) [jkl012]

## Also Nearby

- [ ] Local Museum (45 minutes, 5 miles) [mno345]

## Review / Personal Notes

Great place!
"""
        site = parse_user_data(content)
        assert site.name == "Test Site NHP"
        assert site.visited is False
        assert len(site.cancellation_stamps) == 1
        assert site.cancellation_stamps[0].selected is True
        assert len(site.key_activities) == 2
        assert site.key_activities[0].selected is True
        assert site.key_activities[0].duration_minutes == 45  # avg of 30-60
        assert len(site.hidden_gems) == 1
        assert len(site.also_nearby) == 1

    def test_parse_user_data_visited_checked(self):
        """Parse site with visited checkbox checked."""
        content = """# Visited Site

- [x] Visited

## Cancellation Stamps

## Key Activities

## Hidden Gems

## Also Nearby
"""
        site = parse_user_data(content)
        assert site.visited is True

    def test_parse_user_data_from_file(self, tmp_path):
        """Parse user-data.md from file path."""
        content = """# File Test Site

- [ ] Visited

## Cancellation Stamps

- [ ] VC (Address) [ref1]

## Key Activities

## Hidden Gems

## Also Nearby
"""
        file_path = tmp_path / "user-data.md"
        file_path.write_text(content)

        site = parse_user_data(file_path)
        assert site.name == "File Test Site"
        assert len(site.cancellation_stamps) == 1


class TestIntegrationWithRealFile:
    """Integration tests with actual user-data.md files."""

    def test_parse_abraham_lincoln_birthplace(self):
        """Parse the Abraham Lincoln Birthplace NHP user-data.md."""
        file_path = Path("/workspace/2-Enhanced Data/NPS/Abraham Lincoln Birthplace NHP/user-data.md")
        if not file_path.exists():
            pytest.skip("Test file not available")

        site = parse_user_data(file_path)
        assert site.name == "Abraham Lincoln Birthplace NHP"
        assert len(site.cancellation_stamps) >= 1
        assert len(site.key_activities) >= 1

        # Test duration calculation
        # With the stamp selected (checked), should include 15 min
        duration = site.calculate_selected_duration()
        assert duration >= 15  # At least the stamp time


class TestVisitationSiteInterface:
    """Tests for VisitationSite interface implementation."""

    def test_site_data_implements_visitation_site(self):
        """SiteData should implement VisitationSite protocol."""
        site = SiteData(
            name="Test",
            visited=False,
            cancellation_stamps=[],
            key_activities=[],
            hidden_gems=[],
            also_nearby=[],
        )
        # Should have both required methods
        assert hasattr(site, "should_skip")
        assert hasattr(site, "total_time")
        assert callable(site.should_skip)
        assert callable(site.total_time)

    def test_should_skip_returns_true_when_visited(self):
        """should_skip returns True when site is already visited."""
        site = SiteData(
            name="Test",
            visited=True,
            cancellation_stamps=[],
            key_activities=[],
            hidden_gems=[],
            also_nearby=[],
        )
        assert site.should_skip() is True

    def test_should_skip_returns_false_when_not_visited(self):
        """should_skip returns False when site is not visited."""
        site = SiteData(
            name="Test",
            visited=False,
            cancellation_stamps=[],
            key_activities=[],
            hidden_gems=[],
            also_nearby=[],
        )
        assert site.should_skip() is False

    def test_total_time_returns_selected_duration(self):
        """total_time returns the same as calculate_selected_duration."""
        stamp = CancellationStamp(location="VC", address="a", selected=True, reference_id="x")
        activity = Activity(name="A1", duration_minutes=30, selected=True)
        site = SiteData(
            name="Test",
            visited=False,
            cancellation_stamps=[stamp],
            key_activities=[activity],
            hidden_gems=[],
            also_nearby=[],
        )
        # 15 (stamp) + 30 (activity) = 45
        assert site.total_time() == 45

    def test_total_time_no_selections_returns_zero(self):
        """total_time returns 0 when nothing selected."""
        site = SiteData(
            name="Test",
            visited=False,
            cancellation_stamps=[],
            key_activities=[],
            hidden_gems=[],
            also_nearby=[],
        )
        assert site.total_time() == 0

    def test_isinstance_check_with_protocol(self):
        """SiteData instances should pass isinstance check for VisitationSite."""
        site = SiteData(
            name="Test",
            visited=False,
            cancellation_stamps=[],
            key_activities=[],
            hidden_gems=[],
            also_nearby=[],
        )
        # Protocol check
        assert isinstance(site, VisitationSite)
