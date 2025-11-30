"""
Pluggable Routing Architecture

Provides different routing backends for distance/time calculations:
- HaversineRouter: Fast estimates using straight-line distance
- OSRMRouter: Actual road routing via OSRM (5000 req/min limit)
- GoogleMapsRouter: Google Maps Distance Matrix API (60k elements/min, requires API key)
- CachedRouter: Wraps any router with SQLite caching
"""
from .base import Router, RouteResult, DistanceMatrixResult, DistanceSource
from .haversine import HaversineRouter
from .osrm import OSRMRouter, OSRMError
from .google_maps import GoogleMapsRouter, GoogleMapsError
from .cached import CachedRouter
from .throttle import RateLimiter, ElementRateLimiter

__all__ = [
    # Base interface
    'Router',
    'RouteResult',
    'DistanceMatrixResult',
    'DistanceSource',
    # Implementations
    'HaversineRouter',
    'OSRMRouter',
    'GoogleMapsRouter',
    'CachedRouter',
    # Errors
    'OSRMError',
    'GoogleMapsError',
    # Utilities
    'RateLimiter',
    'ElementRateLimiter',
]
