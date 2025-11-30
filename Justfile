TOP := `git rev-parse --show-toplevel`


claude:
    claude --dangerously-skip-permissions

claude-sonnet:
    claude --dangerously-skip-permissions --model sonnet

claude-haiku:
    claude --dangerously-skip-permissions --model haiku

# mcp-tasks
mcp-tasks-install:
    npm i -g mcp-tasks

mcp-tasks-setup:
    npx mcp-tasks setup tasks.md {{TOP}}

add-task-now TODO_TEXT:
    npx mcp-tasks add "{{TODO_TEXT}}" "To Do" 0

add-task TODO_TEXT:
    npx mcp-tasks add "{{TODO_TEXT}}" "To Do"

task-list:
    npx mcp-tasks
