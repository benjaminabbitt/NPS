"""
Log message constants for routing module.

Following project convention from src/CLAUDE.md.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class LogMessages:
    """Structured log message constants for routing module."""

    # VRP Solver events
    VRP_SOLVING_STARTED = "vrp_solving_started"
    VRP_SOLVING_COMPLETED = "vrp_solving_completed"
    VRP_NO_SOLUTION = "vrp_no_solution"
    VRP_REDUCING_VEHICLES = "vrp_reducing_vehicles"

    # Trip processing events
    TRIP_GENERATED = "trip_generated"
    TRIP_PROCESSING_STARTED = "trip_processing_started"
    TRIP_RESEQUENCING = "trip_resequencing"

    # Operating hours events
    OPERATING_HOURS_VIOLATION = "operating_hours_violation"
    SITES_REMOVED_VIOLATIONS = "sites_removed_due_to_violations"
    START_TIME_ADJUSTED = "start_time_adjusted"

    # Distance calculation events
    DISTANCE_MATRIX_CREATED = "distance_matrix_created"
    TIME_MATRIX_CREATED = "time_matrix_created"

    # Site loading events
    SITES_LOADED = "sites_loaded"
    SITES_FILTERED = "sites_filtered_by_distance"

    # Output events
    OUTPUT_WRITTEN = "output_written"
    GEOJSON_CREATED = "geojson_created"


LOG_MSG = LogMessages()
