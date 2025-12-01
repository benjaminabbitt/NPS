#!/usr/bin/env python3
"""
Update tasks.md to mark completed sites as done
"""
from pathlib import Path


def update_tasks(tasks_file: Path, completed_sites: list[str]):
    """Move completed tasks from To Do to Done section"""

    with open(tasks_file, 'r') as f:
        lines = f.readlines()

    # Find section boundaries
    todo_start = None
    todo_end = None
    done_start = None
    done_end = None

    for i, line in enumerate(lines):
        if line.strip() == '## To Do':
            todo_start = i + 1
        elif line.strip() == '## Done':
            done_start = i + 1
            if todo_start is not None:
                todo_end = i
        elif line.strip() == '## Backlog':
            if done_start is not None:
                done_end = i
            break

    if None in (todo_start, todo_end, done_start):
        print("Error: Could not find all required sections")
        return

    if done_end is None:
        done_end = len(lines)

    # Extract tasks
    todo_tasks = []
    completed_tasks = []

    for i in range(todo_start, todo_end):
        line = lines[i]
        if line.strip().startswith('- [ ]'):
            # Check if this task is in completed_sites
            is_completed = False
            for site in completed_sites:
                if site in line:
                    is_completed = True
                    break

            if is_completed:
                # Mark as done
                completed_task = line.replace('- [ ]', '- [x]')
                completed_tasks.append(completed_task)
            else:
                todo_tasks.append(line)
        elif line.strip() and not line.strip().startswith('#'):
            # Keep non-task lines (comments, blank lines)
            todo_tasks.append(line)

    # Extract existing done tasks
    existing_done = []
    for i in range(done_start, done_end):
        line = lines[i]
        if line.strip():
            existing_done.append(line)

    # Rebuild file
    new_lines = lines[:todo_start]

    # Add To Do section with remaining tasks
    if todo_tasks and todo_tasks[0].strip():
        new_lines.extend(todo_tasks)
    else:
        new_lines.append('\n')
        new_lines.extend([t for t in todo_tasks if t.strip().startswith('- [ ]')])

    # Add blank line before Done
    if not new_lines[-1].strip():
        pass  # Already blank
    else:
        new_lines.append('\n')

    # Add Done section header
    new_lines.append('## Done\n')
    new_lines.append('\n')

    # Add completed tasks (new ones first, then existing)
    new_lines.extend(completed_tasks)
    new_lines.extend(existing_done)

    # Add rest of file from Backlog onward
    new_lines.extend(lines[done_end:])

    # Write back
    with open(tasks_file, 'w') as f:
        f.writelines(new_lines)

    return len(completed_tasks), len(todo_tasks)


def main():
    tasks_file = Path("tasks.md")

    # Batch 3 completed sites
    completed_sites = [
        "El Malpais NM",
        "El Morro NM",
        "Gila Cliff Dwellings NM",
        "Petroglyph NM",
        "Valles Caldera N PRES",
    ]

    print("Updating tasks.md...")
    print(f"Moving {len(completed_sites)} completed sites to Done section:")
    for site in completed_sites:
        print(f"  - {site}")

    completed_count, remaining_count = update_tasks(tasks_file, completed_sites)

    print(f"\n✓ Updated tasks.md")
    print(f"  Completed: {completed_count} tasks")
    print(f"  Remaining: {remaining_count} tasks")


if __name__ == '__main__':
    main()
