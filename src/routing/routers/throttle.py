"""
Rate Limiting / Throttling utilities for API routers.

Provides reusable rate limiting for OSRM and Google Maps APIs.
Thread-safe implementations using locks.
"""
import time
import threading
from dataclasses import dataclass, field
from typing import List, Tuple

# Constants
WINDOW_SECONDS = 60
BUFFER_SECONDS = 0.1  # Small buffer to avoid edge cases


@dataclass
class RateLimiter:
    """
    Thread-safe token bucket rate limiter for API calls.

    Tracks request timestamps and blocks when rate limit is exceeded.
    """
    requests_per_minute: int
    _request_times: List[float] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def wait_if_needed(self) -> float:
        """
        Block if rate limit exceeded. Returns wait time in seconds.
        Thread-safe.
        """
        with self._lock:
            now = time.time()
            # Remove requests older than window
            self._request_times = [t for t in self._request_times if now - t < WINDOW_SECONDS]

            if len(self._request_times) >= self.requests_per_minute:
                oldest = self._request_times[0]
                wait_time = WINDOW_SECONDS - (now - oldest) + BUFFER_SECONDS
                if wait_time > 0:
                    # Release lock while sleeping
                    self._lock.release()
                    try:
                        time.sleep(wait_time)
                    finally:
                        self._lock.acquire()
                    self._request_times = []
                    return wait_time
            return 0.0

    def record_request(self) -> None:
        """Record that a request was made. Thread-safe."""
        with self._lock:
            self._request_times.append(time.time())

    @property
    def requests_remaining(self) -> int:
        """Approximate requests remaining in current window. Thread-safe."""
        with self._lock:
            now = time.time()
            recent = [t for t in self._request_times if now - t < WINDOW_SECONDS]
            return max(0, self.requests_per_minute - len(recent))


@dataclass
class ElementRateLimiter:
    """
    Thread-safe rate limiter for APIs that count elements (origins × destinations).

    Used by Google Maps Distance Matrix API which limits elements per minute.
    """
    elements_per_minute: int
    _element_counts: List[Tuple[float, int]] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def wait_if_needed(self, element_count: int) -> float:
        """
        Block if adding element_count would exceed rate limit.
        Returns wait time in seconds. Thread-safe.
        """
        with self._lock:
            now = time.time()
            # Remove entries older than window
            self._element_counts = [(t, c) for t, c in self._element_counts if now - t < WINDOW_SECONDS]

            current_elements = sum(c for _, c in self._element_counts)

            if current_elements + element_count > self.elements_per_minute:
                if self._element_counts:
                    oldest_time = self._element_counts[0][0]
                    wait_time = WINDOW_SECONDS - (now - oldest_time) + BUFFER_SECONDS
                    if wait_time > 0:
                        # Release lock while sleeping
                        self._lock.release()
                        try:
                            time.sleep(wait_time)
                        finally:
                            self._lock.acquire()
                        self._element_counts = []
                        return wait_time
            return 0.0

    def record_elements(self, count: int) -> None:
        """Record that count elements were requested. Thread-safe."""
        with self._lock:
            self._element_counts.append((time.time(), count))

    @property
    def elements_remaining(self) -> int:
        """Approximate elements remaining in current window. Thread-safe."""
        with self._lock:
            now = time.time()
            recent = sum(c for t, c in self._element_counts if now - t < WINDOW_SECONDS)
            return max(0, self.elements_per_minute - recent)
