---
name: orchestrating-swarms
description: >-
  Orchestrate multi-agent swarms using TeammateTool and Task system. Use when
  coordinating multiple agents, running parallel reviews, building pipeline
  workflows, or implementing divide-and-conquer patterns with subagents.
---

# Swarm orchestration

## Primitives

| Primitive | What It Is |
|-----------|-----------|
| **Agent** | A Claude instance that can use tools. You are an agent. Subagents are agents you spawn. |
| **Team** | A named group of agents working together. One leader, multiple teammates. Config: `~/.claude/teams/{name}/config.json` |
| **Teammate** | An agent that joined a team. Has a name, color, inbox. Spawned via Task with `team_name` + `name`. |
| **Leader** | The agent that created the team. Receives teammate messages, approves plans/shutdowns. |
| **Task** | A work item with subject, description, status, owner, and dependencies. Stored: `~/.claude/tasks/{team}/N.json` |
| **Inbox** | JSON file where an agent receives messages from teammates. Path: `~/.claude/teams/{name}/inboxes/{agent}.json` |
| **Message** | A JSON object sent between agents. Can be text or structured (shutdown_request, idle_notification, etc). |
| **Backend** | How teammates run. Auto-detected: `in-process`, `tmux`, or `iterm2`. See [spawn-backends.md](./references/spawn-backends.md). |

---

## Core Architecture

```
~/.claude/teams/{team-name}/
├── config.json              # Team metadata and member list
└── inboxes/
    ├── team-lead.json       # Leader's inbox
    └── worker-1.json        # Worker inbox

~/.claude/tasks/{team-name}/
├── 1.json                   # Task #1
└── 2.json                   # Task #2
```

---

## Two Ways to Spawn Agents

| Aspect | Task (subagent) | Task + team_name + name (teammate) |
|--------|-----------------|-----------------------------------|
| Lifespan | Until task complete | Until shutdown requested |
| Communication | Return value | Inbox messages |
| Task access | None | Shared task list |
| Team membership | No | Yes |
| Coordination | One-off | Ongoing |
| Best for | Searches, analysis, focused work | Parallel work, pipelines, collaboration |

**Subagent** (short-lived, returns result):
```javascript
Task({ subagent_type: "Explore", description: "Find auth files", prompt: "..." })
```

**Teammate** (persistent, communicates via inbox):
```javascript
Teammate({ operation: "spawnTeam", team_name: "my-project" })
Task({ team_name: "my-project", name: "worker", subagent_type: "general-purpose",
       prompt: "...", run_in_background: true })
```

For detailed agent type descriptions, see [agent-types.md](./references/agent-types.md).

---

## Quick Reference

### Spawn Team + Teammate
```javascript
Teammate({ operation: "spawnTeam", team_name: "my-team" })
Task({ team_name: "my-team", name: "worker", subagent_type: "general-purpose",
       prompt: "...", run_in_background: true })
```

### Message a Teammate
```javascript
Teammate({ operation: "write", target_agent_id: "worker-1", value: "..." })
```

### Create Task Pipeline
```javascript
TaskCreate({ subject: "Step 1", description: "...", activeForm: "Working..." })
TaskCreate({ subject: "Step 2", description: "...", activeForm: "Working..." })
TaskUpdate({ taskId: "2", addBlockedBy: ["1"] })  // #2 waits for #1
```

### Claim and Complete Tasks (as teammate)
```javascript
TaskUpdate({ taskId: "1", owner: "my-name", status: "in_progress" })
// ... do work ...
TaskUpdate({ taskId: "1", status: "completed" })
```

### Shutdown Team
```javascript
Teammate({ operation: "requestShutdown", target_agent_id: "worker-1" })
// Wait for shutdown_approved message...
Teammate({ operation: "cleanup" })
```

---

## Best Practices

1. **Always cleanup** - Don't leave orphaned teams. Call `cleanup` when done.
2. **Use meaningful names** - `security-reviewer`, not `worker-1`.
3. **Write clear prompts** - Tell workers exactly what to do and how to report results.
4. **Use task dependencies** - Let the system manage unblocking via `addBlockedBy`.
5. **Prefer `write` over `broadcast`** - Broadcast sends N messages for N teammates.
6. **Match agent type and model to task** - Explore for reading, Plan for architecture, general-purpose for implementation, specialized reviewers for reviews. For model: use `model: "haiku"` for mechanical isolated tasks (1-2 files, clear spec), default model for multi-file integration, `model: "opus"` for architecture decisions and review.
7. **Handle failures** - Workers have 5-minute heartbeat timeout. Crashed workers' tasks can be reclaimed.
8. **Check inboxes** - Workers send results to your inbox at `~/.claude/teams/{team}/inboxes/team-lead.json`.
9. **Two-stage per-task review** - After each implementation task, dispatch two sequential review subagents: (1) spec compliance ("does the output match the task spec, no more, no less?"), then (2) code quality. Spec compliance must pass before quality review runs. Skip for trivial/mechanical tasks.
10. **Standardize implementer status signals** - Expect teammates to report one of four statuses:
    - **DONE** - Task complete, all tests pass
    - **DONE_WITH_CONCERNS** - Complete but flagging risks (include what and why)
    - **BLOCKED** - Cannot proceed. Escalation: context problem -> provide and re-dispatch; needs more reasoning -> upgrade model; task too large -> split; plan wrong -> escalate to user
    - **NEEDS_CONTEXT** - Missing information to start. Provide context before re-dispatching.
11. **Parallel implementation via worktrees** - Implementation agents share state via git by default, so parallel dispatch causes overwrites. Use `isolation: "worktree"` to give each agent its own copy. Without worktrees, dispatch implementation agents sequentially. Review/research/analysis agents are always safe to parallelize (read-only).
12. **Post-integration verification** - After all agents return: check if agents edited overlapping files (especially with worktrees), review summaries for conflicting approaches, run full test suite, spot-check for systematic errors.
13. **Provide context, don't delegate reading** - Extract task text and include it in the agent prompt. Don't tell agents "read the plan file" -- that wastes their context window on navigation and risks misinterpretation.

---

## References

Detailed documentation for each subsystem:

- [agent-types.md](./references/agent-types.md) - Built-in and plugin agent types with examples
- [teammate-operations.md](./references/teammate-operations.md) - All 13 TeammateTool operations (spawnTeam, write, broadcast, requestShutdown, etc.)
- [task-system.md](./references/task-system.md) - TaskCreate, TaskList, TaskGet, TaskUpdate, dependencies, task file structure
- [message-formats.md](./references/message-formats.md) - All message format JSON examples (regular, shutdown, idle, plan approval, etc.)
- [orchestration-patterns.md](./references/orchestration-patterns.md) - 6 patterns (parallel specialists, pipeline, swarm, research+implementation, plan approval, coordinated refactoring) + 3 complete workflow examples
- [spawn-backends.md](./references/spawn-backends.md) - Backend comparison, auto-detection, in-process/tmux/iterm2 details, troubleshooting
- [environment-config.md](./references/environment-config.md) - Environment variables and team config structure
