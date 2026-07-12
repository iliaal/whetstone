# Codex collaboration quick reference

Use the active tool schemas as the source of truth. Codex collaboration calls are direct tool calls; do not nest them inside an execution-tool script.

## Spawn an agent

```javascript
spawn_agent({
  task_name: "review_auth",
  fork_turns: "all",
  message: "Review authentication boundaries. Return findings only; do not edit files."
})
```

Use one focused task per agent. Fan out independent read-only tasks concurrently up to the environment's active-agent limit.

## Message or continue an agent

```javascript
send_message({ target: "review_auth", message: "Also inspect token rotation." })
followup_task({ target: "review_auth", message: "Re-check the revised implementation." })
```

`send_message` delivers context to a running agent. `followup_task` starts another turn when the target is idle.

## Wait for results

```javascript
wait_agent({ timeout_ms: 30000 })
```

Read the resulting agent message or final status before integrating its work. Use bounded waits so the user still receives progress updates.

## Parallel implementation

Codex agents share the current filesystem. The collaboration schema has no `isolation` argument. Before parallel implementation, use the `ia-git-worktree` skill to create a separate worktree for each agent and include the assigned absolute path in its prompt. Without worktrees, keep implementation serial.

## Task tracking and shutdown

Codex collaboration tools do not expose Claude's `TaskCreate`, `TaskUpdate`, team inbox, or shutdown operations. Track dependencies in the current plan or file-based todos when available. Agents finish their own turns; interrupt a running agent only when its work must stop.
