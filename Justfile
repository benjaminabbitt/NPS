TOP := `git rev-parse --show-toplevel`


claude:
    claude --dangerously-skip-permissions

# mcp-tasks
mcp-tasks-setup:
    npx mcp-tasks setup tasks.md {{TOP}}

add-task-now TODO_TEXT:
    npx mcp-tasks add "{{TODO_TEXT}}" "To Do" 0

add-task TODO_TEXT:
    npx mcp-tasks add "{{TODO_TEXT}}" "To Do"

