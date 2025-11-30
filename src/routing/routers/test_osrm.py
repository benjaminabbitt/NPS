"""Tests for OSRMRouter with mocked HTTP client"""
import pytest
from unittest.mock import Mock, MagicMock
from .osrm import OSRMRouter, OSRMError
from .throttle import RateLimiter
from .base import DistanceSource


class MockHttpResponse:
    """Mock HTTP response for testing"""

    def __init__(self, json_data: dict, status_code: int = 200):
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def json(self) -> dict:
        return self._json_data


class MockHttpClient:
    """Mock HTTP client for testing"""

    def __init__(self):
        self.responses: list[MockHttpResponse] = []
        self.calls: list[tuple[str, dict]] = []

    def add_response(self, json_data: dict, status_code: int = 200):
        self.responses.append(MockHttpResponse(json_data, status_code))

    def get(self, url: str, params: dict = None, timeout: int = 30) -> MockHttpResponse:
        self.calls.append((url, params))
        if self.responses:
            return self.responses.pop(0)
        raise Exception("No mock response configured")


@pytest.fixture
def mock_http_client():
    return MockHttpClient()


@pytest.fixture
def mock_rate_limiter():
    limiter = Mock(spec=RateLimiter)
    limiter.wait_if_needed.return_value = 0.0
    return limiter


@pytest.fixture
def osrm_router(mock_http_client, mock_rate_limiter):
    return OSRMRouter(
        http_client=mock_http_client,
        rate_limiter=mock_rate_limiter,
        base_url="https://test-osrm.example.com",
        profile="driving"
    )


class TestOSRMRouterProperties:
    """Tests for OSRMRouter properties"""

    def test_name_indicates_osrm(self, osrm_router):
        assert "OSRM" in osrm_router.name

    def test_source_is_osrm(self, osrm_router):
        assert osrm_router.source == DistanceSource.OSRM

    def test_is_estimated_false(self, osrm_router):
        """OSRM provides actual road routing, not estimates"""
        assert osrm_router.is_estimated is False


class TestOSRMRouterGetRoute:
    """Tests for get_route method"""

    def test_get_route_success(self, osrm_router, mock_http_client, mock_rate_limiter):
        mock_http_client.add_response({
            "code": "Ok",
            "routes": [{
                "distance": 402336,  # meters (250 miles)
                "duration": 16200    # seconds (270 minutes)
            }]
        })

        result = osrm_router.get_route((38.5831, -90.4068), (37.5504, -85.7346))

        assert result.origin == (38.5831, -90.4068)
        assert result.destination == (37.5504, -85.7346)
        assert abs(result.distance_miles - 250.0) < 1.0
        assert abs(result.duration_minutes - 270.0) < 1.0
        assert result.source == DistanceSource.OSRM
        assert result.is_estimated is False

    def test_get_route_calls_rate_limiter(self, osrm_router, mock_http_client, mock_rate_limiter):
        mock_http_client.add_response({
            "code": "Ok",
            "routes": [{"distance": 1000, "duration": 60}]
        })

        osrm_router.get_route((0, 0), (1, 1))

        mock_rate_limiter.wait_if_needed.assert_called_once()
        mock_rate_limiter.record_request.assert_called_once()

    def test_get_route_formats_url_correctly(self, osrm_router, mock_http_client):
        mock_http_client.add_response({
            "code": "Ok",
            "routes": [{"distance": 1000, "duration": 60}]
        })

        osrm_router.get_route((38.5831, -90.4068), (37.5504, -85.7346))

        url, params = mock_http_client.calls[0]
        assert "https://test-osrm.example.com/route/v1/driving/" in url
        # OSRM uses lon,lat format in URL path
        assert "-90.4068,38.5831" in url
        assert "-85.7346,37.5504" in url
        # Params passed separately
        assert params == {"overview": "false"}

    def test_get_route_raises_on_error_code(self, osrm_router, mock_http_client):
        mock_http_client.add_response({
            "code": "NoRoute",
            "message": "No route found"
        })

        with pytest.raises(OSRMError, match="No route found"):
            osrm_router.get_route((0, 0), (1, 1))

    def test_get_route_raises_on_http_error(self, osrm_router, mock_http_client):
        mock_http_client.add_response({}, status_code=500)

        with pytest.raises(OSRMError, match="OSRM request failed"):
            osrm_router.get_route((0, 0), (1, 1))

    def test_get_route_validates_coordinates(self, osrm_router):
        """Should raise ValueError for invalid coordinates"""
        with pytest.raises(ValueError, match="Invalid latitude"):
            osrm_router.get_route((91, 0), (0, 0))  # lat > 90

        with pytest.raises(ValueError, match="Invalid longitude"):
            osrm_router.get_route((0, 181), (0, 0))  # lon > 180


class TestOSRMRouterDistanceMatrix:
    """Tests for get_distance_matrix method"""

    def test_get_distance_matrix_success(self, osrm_router, mock_http_client):
        mock_http_client.add_response({
            "code": "Ok",
            "distances": [
                [0, 402336],      # meters
                [402336, 0]
            ],
            "durations": [
                [0, 16200],       # seconds
                [16200, 0]
            ]
        })

        origins = [(38.5831, -90.4068), (37.5504, -85.7346)]
        result = osrm_router.get_distance_matrix(origins, origins)

        assert len(result.distances) == 2
        assert len(result.distances[0]) == 2
        assert result.distances[0][0] == 0.0
        assert abs(result.distances[0][1] - 250.0) < 1.0
        assert result.source == DistanceSource.OSRM
        assert result.api_calls_made == 1

    def test_get_distance_matrix_uses_table_api(self, osrm_router, mock_http_client):
        mock_http_client.add_response({
            "code": "Ok",
            "distances": [[0]],
            "durations": [[0]]
        })

        osrm_router.get_distance_matrix([(0, 0)], [(0, 0)])

        url, params = mock_http_client.calls[0]
        assert "/table/v1/driving/" in url
        assert params["annotations"] == "distance,duration"

    def test_get_distance_matrix_handles_null_values(self, osrm_router, mock_http_client):
        """Null values in OSRM response should become infinity"""
        mock_http_client.add_response({
            "code": "Ok",
            "distances": [[0, None], [None, 0]],
            "durations": [[0, None], [None, 0]]
        })

        result = osrm_router.get_distance_matrix([(0, 0), (1, 1)], [(0, 0), (1, 1)])

        assert result.distances[0][1] == float('inf')
        assert result.distances[1][0] == float('inf')
        assert result.durations[0][1] == float('inf')
        assert result.durations[1][0] == float('inf')

    def test_get_distance_matrix_raises_on_size_limit(self, osrm_router, mock_http_client):
        """Should raise error if matrix exceeds 10000 elements"""
        # 101 x 100 = 10100 elements > 10000 limit
        # Use valid coordinates (small increments around a base point)
        origins = [(38.0 + i * 0.001, -90.0 + i * 0.001) for i in range(101)]
        destinations = [(38.0 + i * 0.001, -90.0 + i * 0.001) for i in range(100)]

        with pytest.raises(OSRMError, match="exceeds OSRM limit"):
            osrm_router.get_distance_matrix(origins, destinations)

    def test_get_distance_matrix_raises_on_error_code(self, osrm_router, mock_http_client):
        mock_http_client.add_response({
            "code": "InvalidQuery",
            "message": "Invalid coordinates"
        })

        with pytest.raises(OSRMError, match="Invalid coordinates"):
            osrm_router.get_distance_matrix([(0, 0)], [(1, 1)])


class TestOSRMRouterBatchedMatrix:
    """Tests for get_symmetric_matrix_batched method"""

    def test_batched_matrix_small_set_uses_regular_matrix(self, osrm_router, mock_http_client):
        """Small location sets should use regular symmetric matrix"""
        mock_http_client.add_response({
            "code": "Ok",
            "distances": [[0, 1000], [1000, 0]],
            "durations": [[0, 60], [60, 0]]
        })

        locations = [(0, 0), (1, 1)]
        result = osrm_router.get_symmetric_matrix_batched(locations)

        assert len(mock_http_client.calls) == 1  # Single API call

    def test_batched_matrix_large_set_makes_multiple_calls(self, osrm_router, mock_http_client):
        """Large location sets should be batched into multiple API calls"""
        # Create 150 locations - requires batching at batch_size=100
        locations = [(i * 0.01, i * 0.01) for i in range(150)]

        # Need to provide responses for each batch
        # With 150 locations and batch_size=100:
        # Batch 0-99 x 0-99 (100x100), 0-99 x 100-149 (100x50),
        # 100-149 x 0-99 (50x100), 100-149 x 100-149 (50x50)
        batch_sizes = [
            (100, 100),  # origins 0-99, dests 0-99
            (100, 50),   # origins 0-99, dests 100-149
            (50, 100),   # origins 100-149, dests 0-99
            (50, 50),    # origins 100-149, dests 100-149
        ]
        for rows, cols in batch_sizes:
            mock_http_client.add_response({
                "code": "Ok",
                "distances": [[0] * cols for _ in range(rows)],
                "durations": [[0] * cols for _ in range(rows)]
            })

        result = osrm_router.get_symmetric_matrix_batched(locations, batch_size=100)

        assert len(mock_http_client.calls) == 4
        assert result.api_calls_made == 4


class TestOSRMRouterConversions:
    """Tests for unit conversions"""

    def test_meters_to_miles_conversion(self, osrm_router, mock_http_client):
        mock_http_client.add_response({
            "code": "Ok",
            "routes": [{
                "distance": 1609.34,  # exactly 1 mile in meters
                "duration": 3600
            }]
        })

        result = osrm_router.get_route((0, 0), (1, 1))

        assert abs(result.distance_miles - 1.0) < 0.001

    def test_seconds_to_minutes_conversion(self, osrm_router, mock_http_client):
        mock_http_client.add_response({
            "code": "Ok",
            "routes": [{
                "distance": 1000,
                "duration": 3600  # exactly 60 minutes
            }]
        })

        result = osrm_router.get_route((0, 0), (1, 1))

        assert result.duration_minutes == 60.0


class TestOSRMRouterDefaultFactory:
    """Tests for the create factory method"""

    def test_default_base_url(self, mock_http_client, mock_rate_limiter):
        router = OSRMRouter(mock_http_client, mock_rate_limiter)
        assert router._base_url == "https://router.project-osrm.org"

    def test_default_profile(self, mock_http_client, mock_rate_limiter):
        router = OSRMRouter(mock_http_client, mock_rate_limiter)
        assert router._profile == "driving"

    def test_custom_profile(self, mock_http_client, mock_rate_limiter):
        router = OSRMRouter(mock_http_client, mock_rate_limiter, profile="cycling")
        assert router._profile == "cycling"
