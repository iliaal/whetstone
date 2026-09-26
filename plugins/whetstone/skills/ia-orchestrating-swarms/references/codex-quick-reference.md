# Codex collaboration quick reference

Use the active tool schemas as the source of truth. Codex collaboration calls are direct tool calls; do not nest them inside an execution-tool script.

## Spawn an agent

```javascript
spawn_agent({
  task_name: "review_auth",
  fork_turns: "none",
  message: "Independently review authentication boundaries in /work/project at the supplied revision. Read the specification and changed files. Return verified findings or explicitly no findings, with coverage and limitations. Do not edit files."
})
```

Use one focused task per agent. Fan out independent read-only tasks concurrently up to the environment's active-agent limit.

For independent reviewers, supply the complete task, repository path, revision, criteria, and operative instructions in the prompt. Keep implementation discussion and previous verdicts out of the packet. Spawn a fresh reviewer with `fork_turns: "none"` on every review round; inherited history and a resumed reviewer are not independent review.

## Message or continue an agent

```javascript
send_message({ target: "implement_auth", message: "The assigned token-rotation interface is now available." })
followup_task({ target: "implement_auth", message: "Continue the same authentication unit using the supplied QA findings." })
```

`send_message` delivers context to a running agent. `followup_task` starts another turn when the target is idle.

## Wait for results

```javascript
wait_agent({ timeout_ms: 30000 })
```

Read the resulting agent message or final status before integrating its work. Use bounded waits so the user still receives progress updates.

## Parallel implementation

Codex agents share the current filesystem. The collaboration schema has no `isolation` argument. Use the `ia-git-worktree` skill to create separate worktrees and include each absolute path in its worker prompt, or satisfy every [shared-tree wave condition](./wave-contract.md): committed baseline, exclusive ownership of all write surfaces, no worker git operations, orchestrator-owned aggregate verification, and rollback limited to attributable paths. If either arrangement cannot be established, serialize implementation.

## Task tracking and shutdown

Codex collaboration tools do not expose Claude's `TaskCreate`, `TaskUpdate`, team inbox, or shutdown operations. Track dependencies in the current plan. Agents finish their own turns; interrupt a running agent only when its work must stop.
