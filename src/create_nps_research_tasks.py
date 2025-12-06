#!/usr/bin/env python3
"""
Parse incomplete NPS sites report and create MCP tasks
"""
from pathlib import Path
import re


def parse_incomplete_sites(report_file: Path) -> list[str]:
    """Extract site names from the incomplete sites report"""
    sites = []

    with open(report_file, 'r') as f:
        for line in f:
            # Look for lines that start with "- " (site names)
            if line.startswith('- ') and not line.startswith('  '):
                # Extract site name (between "- " and newline)
                site_name = line[2:].strip()
                if site_name and ':' not in site_name:  # Skip summary lines with colons
                    sites.append(site_name)

    # Remove duplicates while preserving order
    seen = set()
    unique_sites = []
    for site in sites:
        if site not in seen:
            seen.add(site)
            unique_sites.append(site)

    return unique_sites


def create_tasks_md(sites: list[str], tasks_file: Path):
    """Create tasks.md file with all incomplete sites as tasks"""

    # Build task list
    tasks = []
    for site in sorted(sites):
        tasks.append(f"- [ ] Research and complete: {site}")

    # Create tasks.md content
    content = f"""# Tasks - Tasks

## In Progress

## To Do

{chr(10).join(tasks)}

## Done

## Backlog

## Reminders

## Notes
"""

    # Write to file
    with open(tasks_file, 'w') as f:
        f.write(content)

    print(f"Created {len(tasks)} tasks in {tasks_file}")


def main():
    report_file = Path("incomplete_nps_sites.txt")
    tasks_file = Path("tasks.md")

    if not report_file.exists():
        print(f"Error: {report_file} not found")
        return

    print("Parsing incomplete sites report...")
    sites = parse_incomplete_sites(report_file)
    print(f"Found {len(sites)} incomplete sites")

    print(f"\nCreating tasks in {tasks_file}...")
    create_tasks_md(sites, tasks_file)

    print("\n✓ Tasks created successfully")
    print(f"  Total tasks: {len(sites)}")
    print(f"  File: {tasks_file}")


if __name__ == '__main__':
    main()
