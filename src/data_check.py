#!/usr/bin/env python3
"""
Data Check Module

Validates all data in 2-Enhanced Data directory by attempting to load
everything into the appropriate classes and generating a summary.
"""

from pathlib import Path
from typing import List
from dataclasses import dataclass, field

import sys
sys.path.insert(0, str(Path(__file__).parent))

from routing.data_loaders.factory import DataLoaderFactory


@dataclass
class ValidationResult:
    """Result of validating a single item"""
    name: str
    success: bool
    error_message: str = ""
    warnings: List[str] = field(default_factory=list)


@dataclass
class DataCheckSummary:
    """Summary of all data validation"""
    nps_results: List[ValidationResult] = field(default_factory=list)
    worlds_largest_results: List[ValidationResult] = field(default_factory=list)
    parks_results: List[ValidationResult] = field(default_factory=list)

    @property
    def nps_total(self) -> int:
        return len(self.nps_results)

    @property
    def nps_success(self) -> int:
        return sum(1 for r in self.nps_results if r.success)

    @property
    def nps_failed(self) -> int:
        return self.nps_total - self.nps_success

    @property
    def worlds_largest_total(self) -> int:
        return len(self.worlds_largest_results)

    @property
    def worlds_largest_success(self) -> int:
        return sum(1 for r in self.worlds_largest_results if r.success)

    @property
    def parks_total(self) -> int:
        return len(self.parks_results)

    @property
    def parks_success(self) -> int:
        return sum(1 for r in self.parks_results if r.success)

    def format_todo_list(self) -> str:
        """Format as markdown for todo list insertion"""
        lines = [
            "## Data Validation Summary",
            "",
            f"### NPS Sites: {self.nps_success}/{self.nps_total} loaded",
        ]

        if self.nps_failed > 0:
            lines.append(f"- [ ] Fix {self.nps_failed} failed NPS sites")
            for result in self.nps_results:
                if not result.success:
                    lines.append(f"  - [ ] {result.name}: {result.error_message}")

        lines.extend([
            "",
            f"### World's Largest: {self.worlds_largest_success}/{self.worlds_largest_total} loaded",
        ])

        if self.worlds_largest_total - self.worlds_largest_success > 0:
            lines.append(f"- [ ] Fix {self.worlds_largest_total - self.worlds_largest_success} failed World's Largest")

        lines.extend([
            "",
            f"### Amusement Parks: {self.parks_success}/{self.parks_total} loaded",
        ])

        if self.parks_total - self.parks_success > 0:
            lines.append(f"- [ ] Fix {self.parks_total - self.parks_success} failed parks")
            for result in self.parks_results:
                if not result.success:
                    lines.append(f"  - [ ] {result.name}: {result.error_message}")

        return "\n".join(lines)

    def format_detailed_report(self) -> str:
        """Format detailed validation report"""
        lines = [
            "# Data Validation Report",
            "",
            "## NPS Sites",
            f"Total: {self.nps_total}",
            f"Success: {self.nps_success}",
            f"Failed: {self.nps_failed}",
            ""
        ]

        if self.nps_failed > 0:
            lines.append("### Failed NPS Sites:")
            for result in self.nps_results:
                if not result.success:
                    lines.append(f"- **{result.name}**: {result.error_message}")
            lines.append("")

        # Warnings section
        nps_with_warnings = [r for r in self.nps_results if r.success and r.warnings]
        if nps_with_warnings:
            lines.append("### NPS Sites with Warnings:")
            for result in nps_with_warnings[:10]:  # Limit to first 10
                lines.append(f"- **{result.name}**: {', '.join(result.warnings)}")
            if len(nps_with_warnings) > 10:
                lines.append(f"  _(and {len(nps_with_warnings) - 10} more)_")
            lines.append("")

        lines.extend([
            "## World's Largest",
            f"Total: {self.worlds_largest_total}",
            f"Success: {self.worlds_largest_success}",
            f"Failed: {self.worlds_largest_total - self.worlds_largest_success}",
            ""
        ])

        if self.worlds_largest_total - self.worlds_largest_success > 0:
            lines.append("### Failed World's Largest:")
            for result in self.worlds_largest_results:
                if not result.success:
                    lines.append(f"- **{result.name}**: {result.error_message}")
            lines.append("")

        # Warnings for World's Largest
        wl_with_warnings = [r for r in self.worlds_largest_results if r.success and r.warnings]
        if wl_with_warnings:
            lines.append("### World's Largest with Warnings:")
            for result in wl_with_warnings[:10]:
                lines.append(f"- **{result.name}**: {', '.join(result.warnings)}")
            if len(wl_with_warnings) > 10:
                lines.append(f"  _(and {len(wl_with_warnings) - 10} more)_")
            lines.append("")

        lines.extend([
            "## Amusement Parks",
            f"Total: {self.parks_total}",
            f"Success: {self.parks_success}",
            f"Failed: {self.parks_total - self.parks_success}",
            ""
        ])

        if self.parks_total - self.parks_success > 0:
            lines.append("### Failed Parks:")
            for result in self.parks_results:
                if not result.success:
                    lines.append(f"- **{result.name}**: {result.error_message}")
            lines.append("")

        # Warnings for Parks
        parks_with_warnings = [r for r in self.parks_results if r.success and r.warnings]
        if parks_with_warnings:
            lines.append("### Parks with Warnings:")
            for result in parks_with_warnings:
                lines.append(f"- **{result.name}**: {', '.join(result.warnings)}")
            lines.append("")

        return "\n".join(lines)


class DataChecker:
    """Validates all data in 2-Enhanced Data directory"""

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        # Create loaders using factory (with proper dependency injection)
        self.nps_loader = DataLoaderFactory.create_nps_loader()
        self.wl_loader = DataLoaderFactory.create_worlds_largest_loader()
        self.park_loader = DataLoaderFactory.create_amusement_park_loader()

    def check_nps_sites(self) -> List[ValidationResult]:
        """Check all NPS sites"""
        nps_dir = self.base_dir / 'NPS'
        if not nps_dir.exists():
            return [ValidationResult(
                name="NPS Directory",
                success=False,
                error_message=f"Directory not found: {nps_dir}"
            )]

        results = []
        for site_dir in sorted(nps_dir.iterdir()):
            if not site_dir.is_dir():
                continue

            try:
                site_data = self.nps_loader.load_from_directory(site_dir)
                warnings = []

                # Check for missing geocodes
                if site_data.site.lat == 0.0 and site_data.site.lon == 0.0:
                    warnings.append("Missing geocode")

                # Check for empty stamps
                if not site_data.stamps:
                    warnings.append("No stamps found")

                results.append(ValidationResult(
                    name=site_dir.name,
                    success=True,
                    warnings=warnings
                ))
            except Exception as e:
                results.append(ValidationResult(
                    name=site_dir.name,
                    success=False,
                    error_message=str(e)
                ))

        return results

    def check_worlds_largest(self) -> List[ValidationResult]:
        """Check World's Largest attractions"""
        wl_file = Path('/workspace/1-Raw Input Data/World\'s Largest/World\'s Largest.md')

        if not wl_file.exists():
            return [ValidationResult(
                name="World's Largest File",
                success=False,
                error_message=f"File not found: {wl_file}"
            )]

        results = []
        try:
            wl_data = self.wl_loader.load_from_file(wl_file)

            for attraction in wl_data.attractions:
                warnings = []

                # Check for missing geocodes
                if not attraction.geocode:
                    warnings.append("Missing geocode")

                # Check for missing address
                if not attraction.address:
                    warnings.append("Missing address")

                results.append(ValidationResult(
                    name=attraction.name,
                    success=True,
                    warnings=warnings
                ))

            if not wl_data.attractions:
                results.append(ValidationResult(
                    name="World's Largest",
                    success=False,
                    error_message="No attractions found in file"
                ))

        except Exception as e:
            results.append(ValidationResult(
                name="World's Largest",
                success=False,
                error_message=str(e)
            ))

        return results

    def check_amusement_parks(self) -> List[ValidationResult]:
        """Check all amusement parks"""
        parks_dir = self.base_dir / 'Amusement Parks'

        if not parks_dir.exists():
            return [ValidationResult(
                name="Amusement Parks Directory",
                success=False,
                error_message=f"Directory not found: {parks_dir}"
            )]

        results = []
        for park_dir in sorted(parks_dir.iterdir()):
            if not park_dir.is_dir():
                continue

            try:
                park_data = self.park_loader.load_from_directory(park_dir)
                warnings = []

                # Check for missing geocodes
                if park_data.site.lat == 0.0 and park_data.site.lon == 0.0:
                    warnings.append("Missing geocode")

                # Check for empty coasters
                if not park_data.coasters:
                    warnings.append("No coasters found")

                results.append(ValidationResult(
                    name=park_dir.name,
                    success=True,
                    warnings=warnings
                ))
            except Exception as e:
                results.append(ValidationResult(
                    name=park_dir.name,
                    success=False,
                    error_message=str(e)
                ))

        return results

    def check_all(self) -> DataCheckSummary:
        """Check all data and return summary"""
        print("Checking NPS sites...")
        nps_results = self.check_nps_sites()

        print("Checking World's Largest...")
        wl_results = self.check_worlds_largest()

        print("Checking Amusement Parks...")
        parks_results = self.check_amusement_parks()

        return DataCheckSummary(
            nps_results=nps_results,
            worlds_largest_results=wl_results,
            parks_results=parks_results
        )


def main():
    """Run data validation and output summary"""
    base_dir = Path('/workspace/2-Enhanced Data')

    checker = DataChecker(base_dir)
    summary = checker.check_all()

    print("\n" + "=" * 60)
    print(summary.format_detailed_report())
    print("\n" + "=" * 60)
    print("\nTodo List Format:")
    print("=" * 60)
    print(summary.format_todo_list())

    return summary


if __name__ == '__main__':
    main()
