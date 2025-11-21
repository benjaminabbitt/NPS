claude:
TOP := {{trim (run "git" "rev-parse" "--show-toplevel")}}
    claude --dangerously-skip-permissions


# mcp-tasks
mcp-tasks-setup:
    npx mcp-tasks setup tasks.md {{TOP}}

add-task-now:
    npx mcp-tasks add "$1" "To Do" 0

add-task:
    npx mcp-tasks add "$1" "To Do"