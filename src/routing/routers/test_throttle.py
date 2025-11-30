"""Tests for throttle utilities: RateLimiter and ElementRateLimiter"""
import pytest
import time
from unittest.mock import patch
from .throttle import RateLimiter, ElementRateLimiter


class TestRateLimiter:
    """Tests for RateLimiter"""

    def test_create_rate_limiter(self):
        limiter = RateLimiter(requests_per_minute=100)
        assert limiter.requests_per_minute == 100

    def test_initial_requests_remaining(self):
        limiter = RateLimiter(requests_per_minute=100)
        assert limiter.requests_remaining == 100

    def test_record_request_decreases_remaining(self):
        limiter = RateLimiter(requests_per_minute=100)
        limiter.record_request()
        assert limiter.requests_remaining == 99

    def test_multiple_requests_decrease_remaining(self):
        limiter = RateLimiter(requests_per_minute=100)
        for _ in range(10):
            limiter.record_request()
        assert limiter.requests_remaining == 90

    def test_wait_if_needed_returns_zero_when_under_limit(self):
        limiter = RateLimiter(requests_per_minute=100)
        wait_time = limiter.wait_if_needed()
        assert wait_time == 0.0

    def test_requests_remaining_never_negative(self):
        limiter = RateLimiter(requests_per_minute=5)
        for _ in range(10):
            limiter.record_request()
        assert limiter.requests_remaining >= 0

    @patch('time.time')
    @patch('time.sleep')
    def test_old_requests_expire_after_60_seconds(self, mock_sleep, mock_time):
        limiter = RateLimiter(requests_per_minute=100)

        # Record requests at t=0
        mock_time.return_value = 0.0
        for _ in range(50):
            limiter.record_request()

        # At t=61, requests should have expired
        mock_time.return_value = 61.0
        assert limiter.requests_remaining == 100

    @patch('time.time')
    @patch('time.sleep')
    def test_wait_if_needed_blocks_when_at_limit(self, mock_sleep, mock_time):
        limiter = RateLimiter(requests_per_minute=5)

        # Fill up the limit at t=0
        mock_time.return_value = 0.0
        for _ in range(5):
            limiter.record_request()

        # At t=30, still within window, should need to wait
        mock_time.return_value = 30.0
        limiter.wait_if_needed()

        # Should have called sleep
        mock_sleep.assert_called()


class TestElementRateLimiter:
    """Tests for ElementRateLimiter (used by Google Maps)"""

    def test_create_element_limiter(self):
        limiter = ElementRateLimiter(elements_per_minute=60000)
        assert limiter.elements_per_minute == 60000

    def test_initial_elements_remaining(self):
        limiter = ElementRateLimiter(elements_per_minute=60000)
        assert limiter.elements_remaining == 60000

    def test_record_elements_decreases_remaining(self):
        limiter = ElementRateLimiter(elements_per_minute=60000)
        limiter.record_elements(100)
        assert limiter.elements_remaining == 59900

    def test_multiple_element_recordings(self):
        limiter = ElementRateLimiter(elements_per_minute=1000)
        limiter.record_elements(100)
        limiter.record_elements(200)
        limiter.record_elements(300)
        assert limiter.elements_remaining == 400

    def test_wait_if_needed_returns_zero_when_under_limit(self):
        limiter = ElementRateLimiter(elements_per_minute=60000)
        wait_time = limiter.wait_if_needed(100)
        assert wait_time == 0.0

    def test_elements_remaining_never_negative(self):
        limiter = ElementRateLimiter(elements_per_minute=100)
        limiter.record_elements(150)  # Over limit
        assert limiter.elements_remaining >= 0

    @patch('time.time')
    @patch('time.sleep')
    def test_old_elements_expire_after_60_seconds(self, mock_sleep, mock_time):
        limiter = ElementRateLimiter(elements_per_minute=1000)

        # Record elements at t=0
        mock_time.return_value = 0.0
        limiter.record_elements(500)

        # At t=61, elements should have expired
        mock_time.return_value = 61.0
        assert limiter.elements_remaining == 1000

    @patch('time.time')
    @patch('time.sleep')
    def test_wait_if_needed_blocks_when_would_exceed_limit(self, mock_sleep, mock_time):
        limiter = ElementRateLimiter(elements_per_minute=100)

        # Record 80 elements at t=0
        mock_time.return_value = 0.0
        limiter.record_elements(80)

        # At t=30, try to add 30 more (would exceed 100)
        mock_time.return_value = 30.0
        limiter.wait_if_needed(30)

        # Should have called sleep
        mock_sleep.assert_called()

    def test_wait_if_needed_allows_when_under_limit(self):
        limiter = ElementRateLimiter(elements_per_minute=1000)
        limiter.record_elements(100)

        # Should not wait since we're well under limit
        wait_time = limiter.wait_if_needed(100)
        assert wait_time == 0.0
