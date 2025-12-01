#!/usr/bin/env python3
"""
Prioritize NPS sites in specific states by moving them to top of task list
"""
from pathlib import Path
import csv


def get_sites_by_state(csv_file: Path, states: list[str]) -> dict[str, str]:
    """Get mapping of site names to states from CSV"""
    site_states = {}

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header

        for row in reader:
            if len(row) >= 8:
                state = row[7].strip()  # State column
                site_name = row[4].strip()  # Park name column

                if site_name and state in states:
                    site_states[site_name] = state

    return site_states


def reorder_tasks(tasks_file: Path, priority_sites: set[str]):
    """Reorder tasks to put priority sites first"""

    with open(tasks_file, 'r') as f:
        lines = f.readlines()

    # Find the To Do section
    todo_start = None
    todo_end = None

    for i, line in enumerate(lines):
        if line.strip() == '## To Do':
            todo_start = i + 1
        elif todo_start is not None and line.strip().startswith('## '):
            todo_end = i
            break

    if todo_start is None:
        print("Error: Could not find ## To Do section")
        return

    if todo_end is None:
        todo_end = len(lines)

    # Extract tasks
    tasks = []
    non_task_lines = []

    for i in range(todo_start, todo_end):
        line = lines[i]
        if line.strip().startswith('- [ ]'):
            tasks.append(line)
        else:
            non_task_lines.append((i - todo_start, line))

    # Separate priority and other tasks
    priority_tasks = []
    other_tasks = []

    for task in tasks:
        # Extract site name from task
        # Format: "- [ ] Research and complete: SITE NAME"
        if ': ' in task:
            site_name = task.split(': ', 1)[1].strip()

            # Check if this site matches any priority site
            is_priority = False
            for priority_site in priority_sites:
                # Normalize for comparison
                if priority_site.lower() in site_name.lower() or site_name.lower() in priority_site.lower():
                    is_priority = True
                    break

            if is_priority:
                priority_tasks.append(task)
            else:
                other_tasks.append(task)
        else:
            other_tasks.append(task)

    # Rebuild the file
    new_lines = lines[:todo_start]

    # Add empty line after ## To Do
    if non_task_lines and non_task_lines[0][0] == 0:
        new_lines.append(non_task_lines[0][1])
        non_task_lines = non_task_lines[1:]
    else:
        new_lines.append('\n')

    # Add priority tasks first
    new_lines.extend(priority_tasks)

    # Add separator comment
    if priority_tasks:
        new_lines.append('\n')
        new_lines.append('# --- Other Sites ---\n')
        new_lines.append('\n')

    # Add other tasks
    new_lines.extend(other_tasks)

    # Add remaining non-task lines
    for _, line in non_task_lines:
        new_lines.append(line)

    # Add rest of file
    new_lines.extend(lines[todo_end:])

    # Write back
    with open(tasks_file, 'w') as f:
        f.writelines(new_lines)

    return len(priority_tasks), len(other_tasks)


def main():
    csv_file = Path("1-Raw Input Data/NPS/Untitled spreadsheet - US Parks.csv")
    tasks_file = Path("tasks.md")

    # States to prioritize
    priority_states = ['Texas', 'New Mexico', 'Oklahoma']

    print("=" * 70)
    print("PRIORITIZE REGIONAL NPS TASKS")
    print("=" * 70)
    print(f"\nPriority states: {', '.join(priority_states)}")

    # Get sites in priority states
    print("\nFinding sites in priority states...")
    site_states = get_sites_by_state(csv_file, priority_states)

    print(f"Found {len(site_states)} sites:")
    for state in priority_states:
        count = sum(1 for s in site_states.values() if s == state)
        print(f"  {state}: {count} sites")

    # Reorder tasks
    print(f"\nReordering tasks in {tasks_file}...")
    priority_count, other_count = reorder_tasks(tasks_file, set(site_states.keys()))

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Priority tasks (TX, NM, OK): {priority_count}")
    print(f"Other tasks: {other_count}")
    print(f"Total tasks: {priority_count + other_count}")
    print("\n✓ Tasks reordered successfully")


if __name__ == '__main__':
    main()
