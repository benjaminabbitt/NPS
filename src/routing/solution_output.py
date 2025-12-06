#!/usr/bin/env python3
"""
Solution Output Utilities

Manages organized storage of VRP solution outputs with RFC3339 timestamps.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class SolutionOutputManager:
    """
    Manages solution output directories and file naming.

    Creates timestamped directories in solutions/ for each run.
    """

    def __init__(self, base_dir: Path = None):
        """
        Initialize output manager.

        Args:
            base_dir: Base directory for solutions (default: workspace/solutions)
        """
        if base_dir is None:
            # Find workspace root (3 levels up from this file)
            base_dir = Path(__file__).parent.parent.parent / "solutions"

        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_run_directory(self, run_name: Optional[str] = None) -> Path:
        """
        Create a timestamped directory for this run.

        Args:
            run_name: Optional name for the run (appended to timestamp)

        Returns:
            Path to created directory

        Example:
            Without run_name: solutions/2025-12-02T15:30:45Z/
            With run_name: solutions/2025-12-02T15:30:45Z_weekend_trip/
        """
        # Generate RFC3339 timestamp (UTC, with Z suffix)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Create directory name
        if run_name:
            # Sanitize run_name
            safe_name = self._sanitize_name(run_name)
            dir_name = f"{timestamp}_{safe_name}"
        else:
            dir_name = timestamp

        run_dir = self.base_dir / dir_name
        run_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (run_dir / "geojson").mkdir(exist_ok=True)

        return run_dir

    def _sanitize_name(self, name: str) -> str:
        """Sanitize run name for use in directory name"""
        # Replace spaces and special characters
        safe = name.lower().replace(" ", "_")
        # Keep only alphanumeric, underscore, hyphen
        safe = ''.join(c for c in safe if c.isalnum() or c in ('_', '-'))
        # Limit length
        return safe[:50]

    def get_latest_run(self) -> Optional[Path]:
        """Get path to most recent run directory"""
        runs = sorted(self.base_dir.glob("*"))
        return runs[-1] if runs else None

    def list_runs(self, limit: int = 10) -> list[Path]:
        """List recent run directories (newest first)"""
        runs = sorted(self.base_dir.glob("*"), reverse=True)
        return runs[:limit]


def create_solution_directory(run_name: Optional[str] = None) -> Path:
    """
    Convenience function to create a solution output directory.

    Args:
        run_name: Optional descriptive name for the run

    Returns:
        Path to created directory

    Example:
        >>> output_dir = create_solution_directory("weekend_trip")
        >>> print(output_dir)
        /workspace/solutions/2025-12-02T15:30:45Z_weekend_trip/
    """
    manager = SolutionOutputManager()
    return manager.create_run_directory(run_name)


if __name__ == '__main__':
    # Test the solution output manager
    print("Testing SolutionOutputManager...")

    manager = SolutionOutputManager()
    print(f"Base directory: {manager.base_dir}")

    # Create test run
    run_dir = manager.create_run_directory("test_run")
    print(f"Created run directory: {run_dir}")

    # List recent runs
    recent = manager.list_runs(limit=5)
    print(f"\nRecent runs ({len(recent)}):")
    for run in recent:
        print(f"  - {run.name}")

    print("\n✓ SolutionOutputManager validated")
