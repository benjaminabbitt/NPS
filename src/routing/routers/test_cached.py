"""Tests for CachedRouter"""
import pytest
import tempfile
import os
from .cached import CachedRouter
from .haversine import HaversineRouter
from .base import DistanceSource, RouteResult


class TestCachedRouterProperties:
    """Tests for CachedRouter properties"""

    @pytest.fixture
    def temp_cache(self):
        """Create a temporary cache file"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_name_includes_wrapped_router(self, temp_cache):
        inner = HaversineRouter()
        cached = CachedRouter(inner, cache_path=temp_cache)
        assert "Cached" in cached.name
        assert "Haversine" in cached.name

    def test_source_matches_inner_router(self, temp_cache):
        inner = HaversineRouter()
        cached = CachedRouter(inner, cache_path=temp_cache)
        assert cached.source == DistanceSource.HAVERSINE

    def test_is_estimated_matches_inner_router(self, temp_cache):
        inner = HaversineRouter()
        cached = CachedRouter(inner, cache_path=temp_cache)
        assert cached.is_estimated == inner.is_estimated


class TestCachedRouterCaching:
    """Tests for caching behavior"""

    @pytest.fixture
    def temp_cache(self):
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def cached_router(self, temp_cache):
        inner = HaversineRouter()
        return CachedRouter(inner, cache_path=temp_cache)

    def test_first_request_hits_inner_router(self, cached_router):
        result = cached_router.get_route((38.5831, -90.4068), (37.5504, -85.7346))
        assert result.distance_miles > 0
        assert result.duration_minutes > 0

    def test_second_request_returns_cached_result(self, cached_router):
        origin = (38.5831, -90.4068)
        dest = (37.5504, -85.7346)

        result1 = cached_router.get_route(origin, dest)
        result2 = cached_router.get_route(origin, dest)

        assert result1.distance_miles == result2.distance_miles
        assert result1.duration_minutes == result2.duration_minutes

    def test_cached_result_source_is_cache(self, cached_router):
        origin = (38.5831, -90.4068)
        dest = (37.5504, -85.7346)

        # First call - from inner router
        result1 = cached_router.get_route(origin, dest)
        assert result1.source == DistanceSource.HAVERSINE

        # Second call - from cache
        result2 = cached_router.get_route(origin, dest)
        assert result2.source == DistanceSource.CACHE

    def test_different_routes_cached_separately(self, cached_router):
        route1 = cached_router.get_route((38.5831, -90.4068), (37.5504, -85.7346))
        route2 = cached_router.get_route((40.7128, -74.0060), (34.0522, -118.2437))

        assert route1.distance_miles != route2.distance_miles

    def test_cache_stats_tracks_entries(self, cached_router):
        cached_router.get_route((38.5831, -90.4068), (37.5504, -85.7346))
        cached_router.get_route((40.7128, -74.0060), (34.0522, -118.2437))

        stats = cached_router.cache_stats()
        assert stats['total_entries'] == 2

    def test_clear_cache_removes_entries(self, cached_router):
        cached_router.get_route((38.5831, -90.4068), (37.5504, -85.7346))
        cached_router.get_route((40.7128, -74.0060), (34.0522, -118.2437))

        cleared = cached_router.clear_cache()
        assert cleared == 2

        stats = cached_router.cache_stats()
        assert stats['total_entries'] == 0


class TestCachedRouterMatrix:
    """Tests for matrix caching"""

    @pytest.fixture
    def temp_cache(self):
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def cached_router(self, temp_cache):
        inner = HaversineRouter()
        return CachedRouter(inner, cache_path=temp_cache)

    def test_matrix_caches_individual_pairs(self, cached_router):
        locations = [
            (38.5831, -90.4068),
            (37.5504, -85.7346),
            (39.7392, -104.9903),
        ]

        cached_router.get_distance_matrix(locations, locations)

        # Should have cached all 9 pairs (3x3 matrix)
        stats = cached_router.cache_stats()
        assert stats['total_entries'] == 9

    def test_matrix_uses_cache_for_known_pairs(self, cached_router):
        locations = [(38.5831, -90.4068), (37.5504, -85.7346)]

        # First matrix request
        result1 = cached_router.get_distance_matrix(locations, locations)

        # Second matrix request - should use cache
        result2 = cached_router.get_distance_matrix(locations, locations)

        # Results should be identical
        assert result1.distances == result2.distances
        assert result1.durations == result2.durations

        # Second request should make 0 API calls (all from cache)
        assert result2.api_calls_made == 0

    def test_matrix_api_calls_only_for_uncached(self, cached_router):
        # Cache one route
        cached_router.get_route((38.5831, -90.4068), (37.5504, -85.7346))

        locations = [(38.5831, -90.4068), (37.5504, -85.7346)]

        # Matrix request - one pair already cached
        result = cached_router.get_distance_matrix(locations, locations)

        # Should have made 3 calls (4 pairs - 1 cached = 3 new)
        assert result.api_calls_made == 3


class TestCachedRouterPrecision:
    """Tests for coordinate precision/rounding"""

    @pytest.fixture
    def temp_cache(self):
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_coordinates_rounded_to_precision(self, temp_cache):
        inner = HaversineRouter()
        cached = CachedRouter(inner, cache_path=temp_cache, precision=3)

        # These should be treated as the same point after rounding to 3 decimals
        result1 = cached.get_route((38.5831234, -90.4068456), (37.5504, -85.7346))
        result2 = cached.get_route((38.5831999, -90.4068001), (37.5504, -85.7346))

        # Second call should hit cache
        assert result2.source == DistanceSource.CACHE

    def test_different_precision_creates_different_keys(self, temp_cache):
        inner = HaversineRouter()

        # Low precision - treats coords as same
        cached_low = CachedRouter(inner, cache_path=temp_cache, precision=2)
        result1 = cached_low.get_route((38.581, -90.406), (37.55, -85.73))
        result2 = cached_low.get_route((38.589, -90.409), (37.55, -85.73))

        # After rounding to 2 decimals: 38.58 vs 38.59 - different!
        # So second call won't hit cache
        assert result2.source == DistanceSource.HAVERSINE
