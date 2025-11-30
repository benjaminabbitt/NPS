"""
Error message constants for routing module.

Following project convention from src/CLAUDE.md.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorMessages:
    """Error message constants for routing module."""

    # Input validation errors
    INVALID_HOURS_PER_DAY = "hours_per_day must be between 0 and 24"
    INVALID_SPEED = "avg_speed_mph must be positive"
    INVALID_VISIT_TIME = "visit_hours_per_site must be positive"
    INVALID_MIN_SITES = "min_sites_per_day must be non-negative"
    INVALID_MAX_SITES = "max_sites_per_day must be greater than min_sites_per_day"
    INVALID_TARGET_DAYS = "target_days must be positive"
    EMPTY_SITES_LIST = "sites list cannot be empty"
    INVALID_HOME_BASE = "home_base must be (name, lat, lon) tuple"

    # Coordinate errors
    INVALID_LATITUDE = "Invalid latitude: must be between -90 and 90"
    INVALID_LONGITUDE = "Invalid longitude: must be between -180 and 180"

    # VRP solver errors
    NO_SOLUTION_FOUND = "No solution found for VRP problem"
    SOLVER_TIMEOUT = "VRP solver timed out"

    # Operating hours errors
    OPERATING_HOURS_VIOLATION = "Site visit outside operating hours"


ERROR_MSG = ErrorMessages()
