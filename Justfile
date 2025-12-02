TOP := `git rev-parse --show-toplevel`


claude:
    claude --dangerously-skip-permissions

claudeResume:
    claude --dangerously-skip-permissions --continue

claudeProcessTodo:
    claude --dangerously-skip-permissions Use MCP todo list.  Spawn 10 subagents and process the top of the todo list.  Ensure you keep MCP todo list updated.

# mcp-tasks
mcp-tasks-setup:
    npx mcp-tasks setup tasks.md {{TOP}}

add-task-now TODO_TEXT:
    npx mcp-tasks add "{{TODO_TEXT}}" "To Do" 0

add-task TODO_TEXT:
    npx mcp-tasks add "{{TODO_TEXT}}" "To Do"

# Routing / Trip Planning

# Generate St. Louis 3-day trips with 300 mile radius
# - Uses two-phase VRP with flexible operating hours
# - Allows early arrivals (user can wait), only flags late arrivals as violations
# - Automatically rolls sites to next day if arriving too late
# - Dynamic start times optimized for first site of each day
stl-trips:
    uv run python3 src/routing/vrp_trip_planner.py \
        --home "Kirkwood, MO" \
        --max-distance 300 \
        --target-days 3 \
        --output results/stl_3day.yaml

# Optimize trip parameters to find maximum coverage with zero violations
# - Uses binary search to find optimal max-distance parameter
# - Default: 3-day trips, auto-calculated max distance (660 miles for 3 days)
# - Customize: just optimize-trips DAYS=7 for 7-day trips (1540 miles max)
optimize-trips DAYS="3":
    uv run python3 src/routing/optimize_trip_parameters.py \
        --target-days {{DAYS}}

# Generate trips from different home base
# Example: just plan-trips "Denver, CO" 39.7392 -104.9903 7
plan-trips HOME LAT LON DAYS="3":
    uv run python3 src/routing/vrp_trip_planner.py \
        --home "{{HOME}}" \
        --lat {{LAT}} \
        --lon {{LON}} \
        --target-days {{DAYS}} \
        --output results/{{HOME}}_{{DAYS}}day.yaml

