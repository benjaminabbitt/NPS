"""Tests for GoogleMapsRouter with mocked HTTP client"""
import pytest
from unittest.mock import Mock
from .google_maps import GoogleMapsRouter, GoogleMapsError
from .throttle import ElementRateLimiter
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
    limiter = Mock(spec=ElementRateLimiter)
    limiter.wait_if_needed.return_value = 0.0
    return limiter


@pytest.fixture
def google_maps_router(mock_http_client, mock_rate_limiter):
    return GoogleMapsRouter(
        http_client=mock_http_client,
        rate_limiter=mock_rate_limiter,
        api_key="test-api-key"
    )


class TestGoogleMapsRouterProperties:
    """Tests for GoogleMapsRouter properties"""

    def test_name_indicates_google_maps(self, google_maps_router):
        assert "Google Maps" in google_maps_router.name

    def test_source_is_google_maps(self, google_maps_router):
        assert google_maps_router.source == DistanceSource.GOOGLE_MAPS

    def test_is_estimated_false(self, google_maps_router):
        """Google Maps provides actual road routing, not estimates"""
        assert google_maps_router.is_estimated is False


class TestGoogleMapsRouterGetRoute:
    """Tests for get_route method"""

    def test_get_route_success(self, google_maps_router, mock_http_client, mock_rate_limiter):
        mock_http_client.add_response({
            "status": "OK",
            "rows": [{
                "elements": [{
                    "status": "OK",
                    "distance": {"value": 402336},  # meters (250 miles)
                    "duration": {"value": 16200}    # seconds (270 minutes)
                }]
            }]
        })

        result = google_maps_router.get_route((38.5831, -90.4068), (37.5504, -85.7346))

        assert result.origin == (38.5831, -90.4068)
        assert result.destination == (37.5504, -85.7346)
        assert abs(result.distance_miles - 250.0) < 1.0
        assert abs(result.duration_minutes - 270.0) < 1.0
        assert result.source == DistanceSource.GOOGLE_MAPS
        assert result.is_estimated is False

    def test_get_route_calls_rate_limiter(self, google_maps_router, mock_http_client, mock_rate_limiter):
        mock_http_client.add_response({
            "status": "OK",
            "rows": [{
                "elements": [{
                    "status": "OK",
                    "distance": {"value": 1000},
                    "duration": {"value": 60}
                }]
            }]
        })

        google_maps_router.get_route((0, 0), (1, 1))

        # Should have called with 1 element (1 origin × 1 destination)
        mock_rate_limiter.wait_if_needed.assert_called_once_with(1)
        mock_rate_limiter.record_elements.assert_called_once_with(1)

    def test_get_route_formats_params_correctly(self, google_maps_router, mock_http_client):
        mock_http_client.add_response({
            "status": "OK",
            "rows": [{
                "elements": [{
                    "status": "OK",
                    "distance": {"value": 1000},
                    "duration": {"value": 60}
                }]
            }]
        })

        google_maps_router.get_route((38.5831, -90.4068), (37.5504, -85.7346))

        url, params = mock_http_client.calls[0]
        assert url == "https://maps.googleapis.com/maps/api/distancematrix/json"
        assert params["key"] == "test-api-key"
        assert params["units"] == "imperial"
        # Google Maps uses lat,lng format
        assert "38.5831,-90.4068" in params["origins"]
        assert "37.5504,-85.7346" in params["destinations"]

    def test_get_route_raises_on_api_error(self, google_maps_router, mock_http_client):
        mock_http_client.add_response({
            "status": "REQUEST_DENIED",
            "error_message": "API key invalid"
        })

        with pytest.raises(GoogleMapsError, match="API key invalid"):
            google_maps_router.get_route((0, 0), (1, 1))

    def test_get_route_raises_on_element_error(self, google_maps_router, mock_http_client):
        mock_http_client.add_response({
            "status": "OK",
            "rows": [{
                "elements": [{
                    "status": "ZERO_RESULTS"
                }]
            }]
        })

        with pytest.raises(GoogleMapsError, match="Route not found"):
            google_maps_router.get_route((0, 0), (1, 1))

    def test_get_route_raises_on_http_error(self, google_maps_router, mock_http_client):
        mock_http_client.add_response({}, status_code=500)

        with pytest.raises(GoogleMapsError, match="Google Maps request failed"):
            google_maps_router.get_route((0, 0), (1, 1))


class TestGoogleMapsRouterDistanceMatrix:
    """Tests for get_distance_matrix method"""

    def test_get_distance_matrix_success(self, google_maps_router, mock_http_client):
        mock_http_client.add_response({
            "status": "OK",
            "rows": [
                {
                    "elements": [
                        {"status": "OK", "distance": {"value": 0}, "duration": {"value": 0}},
                        {"status": "OK", "distance": {"value": 402336}, "duration": {"value": 16200}}
                    ]
                },
                {
                    "elements": [
                        {"status": "OK", "distance": {"value": 402336}, "duration": {"value": 16200}},
                        {"status": "OK", "distance": {"value": 0}, "duration": {"value": 0}}
                    ]
                }
            ]
        })

        origins = [(38.5831, -90.4068), (37.5504, -85.7346)]
        result = google_maps_router.get_distance_matrix(origins, origins)

        assert len(result.distances) == 2
        assert len(result.distances[0]) == 2
        assert result.distances[0][0] == 0.0
        assert abs(result.distances[0][1] - 250.0) < 1.0
        assert result.source == DistanceSource.GOOGLE_MAPS
        assert result.api_calls_made == 1

    def test_get_distance_matrix_handles_no_route(self, google_maps_router, mock_http_client):
        """Elements with no route should become infinity"""
        mock_http_client.add_response({
            "status": "OK",
            "rows": [{
                "elements": [
                    {"status": "OK", "distance": {"value": 0}, "duration": {"value": 0}},
                    {"status": "ZERO_RESULTS"}
                ]
            }]
        })

        result = google_maps_router.get_distance_matrix([(0, 0)], [(0, 0), (90, 0)])

        assert result.distances[0][0] == 0.0
        assert result.distances[0][1] == float('inf')
        assert result.durations[0][1] == float('inf')

    def test_get_distance_matrix_raises_on_api_error(self, google_maps_router, mock_http_client):
        mock_http_client.add_response({
            "status": "OVER_QUERY_LIMIT"
        })

        with pytest.raises(GoogleMapsError, match="OVER_QUERY_LIMIT"):
            google_maps_router.get_distance_matrix([(0, 0)], [(1, 1)])

    def test_get_distance_matrix_element_count_for_rate_limiter(
        self, google_maps_router, mock_http_client, mock_rate_limiter
    ):
        mock_http_client.add_response({
            "status": "OK",
            "rows": [
                {"elements": [
                    {"status": "OK", "distance": {"value": 0}, "duration": {"value": 0}},
                    {"status": "OK", "distance": {"value": 1000}, "duration": {"value": 60}},
                    {"status": "OK", "distance": {"value": 2000}, "duration": {"value": 120}}
                ]}
            ]
        })

        google_maps_router.get_distance_matrix([(0, 0)], [(1, 1), (2, 2), (3, 3)])

        # 1 origin × 3 destinations = 3 elements
        mock_rate_limiter.wait_if_needed.assert_called_with(3)
        mock_rate_limiter.record_elements.assert_called_with(3)


class TestGoogleMapsRouterBatching:
    """Tests for automatic batching behavior"""

    def test_batches_when_too_many_destinations(self, google_maps_router, mock_http_client):
        """Should batch when destinations exceed 25"""
        # 30 destinations with 1 origin needs 2 batches
        # Batch 1: 25 destinations, Batch 2: 5 destinations
        mock_http_client.add_response({
            "status": "OK",
            "rows": [{"elements": [
                {"status": "OK", "distance": {"value": i * 1000}, "duration": {"value": i * 60}}
                for i in range(25)
            ]}]
        })
        mock_http_client.add_response({
            "status": "OK",
            "rows": [{"elements": [
                {"status": "OK", "distance": {"value": i * 1000}, "duration": {"value": i * 60}}
                for i in range(5)
            ]}]
        })

        origins = [(0, 0)]
        destinations = [(i * 0.01, i * 0.01) for i in range(30)]

        result = google_maps_router.get_distance_matrix(origins, destinations)

        assert len(mock_http_client.calls) == 2
        assert result.api_calls_made == 2
        assert len(result.distances[0]) == 30

    def test_batches_when_too_many_elements(self, google_maps_router, mock_http_client):
        """Should batch when total elements exceed 100"""
        # With 5 origins, dest_batch_size = min(25, 100//5) = 20
        # So 25 destinations split into: batch of 20, batch of 5
        # Each batch: 5 origins × 20 dests = 100 elements, 5 origins × 5 dests = 25 elements
        mock_http_client.add_response({
            "status": "OK",
            "rows": [
                {"elements": [
                    {"status": "OK", "distance": {"value": j * 1000}, "duration": {"value": j * 60}}
                    for j in range(20)  # First 20 destinations
                ]}
                for _ in range(5)  # All 5 origins
            ]
        })
        mock_http_client.add_response({
            "status": "OK",
            "rows": [
                {"elements": [
                    {"status": "OK", "distance": {"value": j * 1000}, "duration": {"value": j * 60}}
                    for j in range(5)  # Last 5 destinations
                ]}
                for _ in range(5)  # All 5 origins
            ]
        })

        origins = [(i * 0.01, i * 0.01) for i in range(5)]
        destinations = [(i * 0.01, i * 0.01) for i in range(25)]

        result = google_maps_router.get_distance_matrix(origins, destinations)

        assert len(mock_http_client.calls) == 2
        assert result.api_calls_made == 2
        assert len(result.distances) == 5
        assert len(result.distances[0]) == 25


class TestGoogleMapsRouterConversions:
    """Tests for unit conversions"""

    def test_meters_to_miles_conversion(self, google_maps_router, mock_http_client):
        mock_http_client.add_response({
            "status": "OK",
            "rows": [{
                "elements": [{
                    "status": "OK",
                    "distance": {"value": 1609.34},  # exactly 1 mile in meters
                    "duration": {"value": 3600}
                }]
            }]
        })

        result = google_maps_router.get_route((0, 0), (1, 1))

        assert abs(result.distance_miles - 1.0) < 0.001

    def test_seconds_to_minutes_conversion(self, google_maps_router, mock_http_client):
        mock_http_client.add_response({
            "status": "OK",
            "rows": [{
                "elements": [{
                    "status": "OK",
                    "distance": {"value": 1000},
                    "duration": {"value": 3600}  # exactly 60 minutes
                }]
            }]
        })

        result = google_maps_router.get_route((0, 0), (1, 1))

        assert result.duration_minutes == 60.0


class TestGoogleMapsRouterFactory:
    """Tests for create factory method validation"""

    def test_api_key_stored(self, mock_http_client, mock_rate_limiter):
        router = GoogleMapsRouter(
            http_client=mock_http_client,
            rate_limiter=mock_rate_limiter,
            api_key="my-secret-key"
        )
        assert router._api_key == "my-secret-key"

    def test_api_key_used_in_requests(self, google_maps_router, mock_http_client):
        mock_http_client.add_response({
            "status": "OK",
            "rows": [{
                "elements": [{
                    "status": "OK",
                    "distance": {"value": 1000},
                    "duration": {"value": 60}
                }]
            }]
        })

        google_maps_router.get_route((0, 0), (1, 1))

        _, params = mock_http_client.calls[0]
        assert params["key"] == "test-api-key"
