"""
Cached Router

Wraps any Router implementation with a caching layer to avoid redundant API calls.
Uses SQLite for persistent caching across sessions.
"""
import json
import sqlite3
import hashlib
from pathlib import Path
from typing import List, Tuple, Optional

from .base import Router, RouteResult, DistanceMatrixResult, DistanceSource


class CachedRouter(Router):
    """
    Caching wrapper for any Router implementation.

    Caches route results in SQLite database to avoid redundant API calls.
    Cache keys are based on origin/destination coordinates.
    """

    def __init__(
        self,
        router: Router,
        cache_path: str = None,
        precision: int = 5  # Decimal places for coordinate rounding
    ):
        """
        Initialize cached router.

        Args:
            router: The underlying router to wrap
            cache_path: Path to SQLite cache file (default: ~/.cache/routing_cache.db)
            precision: Decimal precision for coordinate rounding (default: 5 = ~1m accuracy)
        """
        self._router = router
        self._precision = precision

        if cache_path is None:
            cache_dir = Path.home() / ".cache"
            cache_dir.mkdir(exist_ok=True)
            cache_path = str(cache_dir / "routing_cache.db")

        self._cache_path = cache_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database schema."""
        with sqlite3.connect(self._cache_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS route_cache (
                    cache_key TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    origin_lat REAL NOT NULL,
                    origin_lon REAL NOT NULL,
                    dest_lat REAL NOT NULL,
                    dest_lon REAL NOT NULL,
                    distance_miles REAL NOT NULL,
                    duration_minutes REAL NOT NULL,
                    is_estimated INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_route_cache_source
                ON route_cache(source)
            """)
            conn.commit()

    def _make_cache_key(self, origin: Tuple[float, float], destination: Tuple[float, float]) -> str:
        """Create cache key from coordinates and router source."""
        lat1 = round(origin[0], self._precision)
        lon1 = round(origin[1], self._precision)
        lat2 = round(destination[0], self._precision)
        lon2 = round(destination[1], self._precision)
        key_str = f"{self._router.source.value}:{lat1},{lon1}:{lat2},{lon2}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_cached_route(self, origin: Tuple[float, float], destination: Tuple[float, float]) -> Optional[RouteResult]:
        """Retrieve cached route if available."""
        cache_key = self._make_cache_key(origin, destination)

        with sqlite3.connect(self._cache_path) as conn:
            cursor = conn.execute(
                "SELECT distance_miles, duration_minutes, is_estimated FROM route_cache WHERE cache_key = ?",
                (cache_key,)
            )
            row = cursor.fetchone()

        if row:
            return RouteResult(
                origin=origin,
                destination=destination,
                distance_miles=row[0],
                duration_minutes=row[1],
                source=DistanceSource.CACHE,
                is_estimated=bool(row[2])
            )
        return None

    def _cache_route(self, result: RouteResult) -> None:
        """Store route result in cache."""
        cache_key = self._make_cache_key(result.origin, result.destination)

        with sqlite3.connect(self._cache_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO route_cache
                (cache_key, source, origin_lat, origin_lon, dest_lat, dest_lon,
                 distance_miles, duration_minutes, is_estimated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cache_key,
                result.source.value,
                result.origin[0], result.origin[1],
                result.destination[0], result.destination[1],
                result.distance_miles,
                result.duration_minutes,
                int(result.is_estimated)
            ))
            conn.commit()

    @property
    def name(self) -> str:
        return f"Cached({self._router.name})"

    @property
    def source(self) -> DistanceSource:
        return self._router.source

    @property
    def is_estimated(self) -> bool:
        return self._router.is_estimated

    def get_route(self, origin: Tuple[float, float], destination: Tuple[float, float]) -> RouteResult:
        # Check cache first
        cached = self._get_cached_route(origin, destination)
        if cached:
            return cached

        # Get from underlying router
        result = self._router.get_route(origin, destination)

        # Cache the result
        self._cache_route(result)

        return result

    def get_distance_matrix(
        self,
        origins: List[Tuple[float, float]],
        destinations: List[Tuple[float, float]]
    ) -> DistanceMatrixResult:
        """
        Get distance matrix, using cache where possible.

        For matrix requests, we check cache for each pair and only
        request uncached pairs from the underlying router.
        """
        num_origins = len(origins)
        num_destinations = len(destinations)

        distances: List[List[float]] = [[0.0] * num_destinations for _ in range(num_origins)]
        durations: List[List[float]] = [[0.0] * num_destinations for _ in range(num_origins)]

        # Track which pairs need to be fetched
        uncached_pairs: List[Tuple[int, int, Tuple[float, float], Tuple[float, float]]] = []

        # Check cache for each pair
        for i, origin in enumerate(origins):
            for j, dest in enumerate(destinations):
                cached = self._get_cached_route(origin, dest)
                if cached:
                    distances[i][j] = cached.distance_miles
                    durations[i][j] = cached.duration_minutes
                else:
                    uncached_pairs.append((i, j, origin, dest))

        # If all pairs were cached, return immediately
        if not uncached_pairs:
            return DistanceMatrixResult(
                origins=origins,
                destinations=destinations,
                distances=distances,
                durations=durations,
                source=DistanceSource.CACHE,
                is_estimated=self._router.is_estimated,
                api_calls_made=0
            )

        # Fetch uncached pairs - for simplicity, fetch individual routes
        # (Could optimize by batching into matrix request for uncached subset)
        api_calls = 0
        for i, j, origin, dest in uncached_pairs:
            result = self._router.get_route(origin, dest)
            api_calls += 1
            distances[i][j] = result.distance_miles
            durations[i][j] = result.duration_minutes
            self._cache_route(result)

        return DistanceMatrixResult(
            origins=origins,
            destinations=destinations,
            distances=distances,
            durations=durations,
            source=self._router.source,
            is_estimated=self._router.is_estimated,
            api_calls_made=api_calls
        )

    def clear_cache(self) -> int:
        """Clear all cached routes. Returns number of entries cleared."""
        with sqlite3.connect(self._cache_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM route_cache")
            count = cursor.fetchone()[0]
            conn.execute("DELETE FROM route_cache")
            conn.commit()
        return count

    def cache_stats(self) -> dict:
        """Get cache statistics."""
        with sqlite3.connect(self._cache_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM route_cache")
            total = cursor.fetchone()[0]

            cursor = conn.execute("SELECT source, COUNT(*) FROM route_cache GROUP BY source")
            by_source = dict(cursor.fetchall())

        return {
            "total_entries": total,
            "by_source": by_source,
            "cache_path": self._cache_path
        }
