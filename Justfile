claude:
    claude --dangerously-skip-permissions


# mcp-tasks
mcp-tasks-setup:
    npx mcp-tasks setup tasks.md $PWD

add-task-now:
    npx mcp-tasks add "$1" "To Do" 0

add-task:
    npx mcp-tasks add "$1" "To Do"