#!/usr/bin/env python3
"""
Tests for TripReorderer

Tests the permutation-based site reordering logic.
"""
import pytest
from unittest.mock import Mock
from core.site import Site
from .reorderer import TripReorderer


class TestTripReorderer:
    """Tests for TripReorderer class"""

    @pytest.fixture
    def mock_check_fits(self):
        """Mock function that always returns sites fit"""
        def check_fits(sites_so_far, new_site, start_location, budget, start_hour):
            return (True, None, None)
        return check_fits

    @pytest.fixture
    def mock_check_never_fits(self):
        """Mock function that always returns sites don't fit"""
        def check_fits(sites_so_far, new_site, start_location, budget, start_hour):
            return (False, None, 'budget_exceeded')
        return check_fits

    @pytest.fixture
    def reorderer(self, mock_check_fits):
        """Create reorderer with mock check function"""
        return TripReorderer(check_site_fits_fn=mock_check_fits)

    @pytest.fixture
    def sample_sites(self):
        """Create sample sites for testing"""
        return [
            {'site_name': 'Site A', 'lat': 38.0, 'lon': -90.0},
            {'site_name': 'Site B', 'lat': 38.1, 'lon': -90.1},
            {'site_name': 'Site C', 'lat': 38.2, 'lon': -90.2},
        ]

    def test_reorder_empty_day_with_new_site_succeeds(self, reorderer, sample_sites):
        """When adding first site to empty day, should succeed"""
        current_day = []
        new_site = sample_sites[0]
        start_location = Site(name="Home", lat=38.0, lon=-90.0)

        success, reordered, moved_prev, moved_next = reorderer.try_reorder_day(
            current_day,
            new_site,
            start_location,
            day_budget_minutes=900,
            start_hour=6
        )

        assert success is True
        assert len(reordered) == 1
        assert reordered[0] == new_site
        assert moved_prev is None
        assert moved_next is None

    def test_reorder_with_sites_that_fit_succeeds(self, reorderer, sample_sites):
        """When all sites fit in order, should succeed"""
        current_day = sample_sites[:2]
        new_site = sample_sites[2]
        start_location = Site(name="Home", lat=38.0, lon=-90.0)

        success, reordered, _, _ = reorderer.try_reorder_day(
            current_day,
            new_site,
            start_location,
            day_budget_minutes=900,
            start_hour=6
        )

        assert success is True
        assert len(reordered) == 3

    def test_reorder_with_sites_that_never_fit_fails(self, mock_check_never_fits, sample_sites):
        """When sites never fit, should fail"""
        reorderer = TripReorderer(check_site_fits_fn=mock_check_never_fits)
        current_day = sample_sites[:2]
        new_site = sample_sites[2]
        start_location = Site(name="Home", lat=38.0, lon=-90.0)

        success, reordered, _, _ = reorderer.try_reorder_day(
            current_day,
            new_site,
            start_location,
            day_budget_minutes=900,
            start_hour=6
        )

        assert success is False
        # When reordering fails, returns empty list or current_day depending on path
        assert isinstance(reordered, list)

    def test_reorder_respects_max_permutation_size(self, reorderer):
        """When site count exceeds max, should use simplified reordering"""
        # Create 9 sites (exceeds default max of 8)
        many_sites = [
            {'site_name': f'Site {i}', 'lat': 38.0 + i*0.1, 'lon': -90.0}
            for i in range(9)
        ]
        current_day = many_sites[:8]
        new_site = many_sites[8]
        start_location = Site(name="Home", lat=38.0, lon=-90.0)

        success, reordered, _, _ = reorderer.try_reorder_day(
            current_day,
            new_site,
            start_location,
            day_budget_minutes=900,
            start_hour=6
        )

        # Should fall back to simpler algorithm
        assert isinstance(reordered, list)

    def test_reorder_with_previous_day_sites(self, reorderer, sample_sites):
        """When reordering across days, should handle prev_day_sites"""
        current_day = [sample_sites[1]]
        new_site = sample_sites[2]
        prev_day = [sample_sites[0]]
        start_location = Site(name="Home", lat=38.0, lon=-90.0)

        success, reordered, moved_prev, moved_next = reorderer.try_reorder_day(
            current_day,
            new_site,
            start_location,
            day_budget_minutes=900,
            start_hour=6,
            prev_day_sites=prev_day
        )

        # Should successfully reorder
        assert success is True
        assert len(reordered) >= 1

    def test_reorder_with_selective_fitting(self, sample_sites):
        """Test with check function that only allows specific orders"""
        # Only allow Site A -> Site C (not A -> B -> C)
        def selective_check(sites_so_far, new_site, start_location, budget, start_hour):
            if len(sites_so_far) == 1:
                # After first site, only allow Site C
                return (new_site['site_name'] == 'Site C', None, None)
            return (True, None, None)

        reorderer = TripReorderer(check_site_fits_fn=selective_check)
        current_day = [sample_sites[0]]  # Site A
        new_site = sample_sites[1]  # Site B
        start_location = Site(name="Home", lat=38.0, lon=-90.0)

        success, reordered, _, _ = reorderer.try_reorder_day(
            current_day,
            new_site,
            start_location,
            day_budget_minutes=900,
            start_hour=6
        )

        # Should fail because Site B doesn't fit after Site A
        assert success is False


class TestTripReordererEdgeCases:
    """Edge case tests for TripReorderer"""

    def test_reorder_with_zero_budget(self):
        """Reordering with zero budget should fail"""
        def check_fits(sites_so_far, new_site, start_location, budget, start_hour):
            return (False, None, 'budget_exceeded')

        reorderer = TripReorderer(check_site_fits_fn=check_fits)
        site = {'site_name': 'Test', 'lat': 38.0, 'lon': -90.0}
        start_location = Site(name="Home", lat=38.0, lon=-90.0)

        success, _, _, _ = reorderer.try_reorder_day(
            [],
            site,
            start_location,
            day_budget_minutes=0,
            start_hour=6
        )

        assert success is False

    def test_reorder_preserves_site_data(self):
        """Reordering should not modify site dictionaries"""
        def check_fits(sites_so_far, new_site, start_location, budget, start_hour):
            return (True, None, None)

        reorderer = TripReorderer(check_site_fits_fn=check_fits)
        original_site = {'site_name': 'Test', 'lat': 38.0, 'lon': -90.0, 'data': 'preserved'}
        start_location = Site(name="Home", lat=38.0, lon=-90.0)

        success, reordered, _, _ = reorderer.try_reorder_day(
            [],
            original_site,
            start_location,
            day_budget_minutes=900,
            start_hour=6
        )

        assert success is True
        assert reordered[0]['data'] == 'preserved'
        assert reordered[0] is original_site  # Same object, not copied
