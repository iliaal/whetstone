---
name: orchestrating-swarms
description: >-
  Coordinate multi-agent swarms for parallel and pipeline workflows. Use when
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

## Dispatch Discipline

Rules for when and how to dispatch agents. Getting these wrong wastes tokens and creates hard-to-debug failures.

**When to dispatch a team vs. do it yourself:**

Assess 5 signals: file count, module span, dependency chain, risk surface, parallelism potential. If 3+ fall in the "complex" column, dispatch a team. Below 3, do it yourself. When in doubt, prefer the simple path -- team overhead is only justified when parallelism provides a real speedup.

**Provide full context, never delegate navigation:**

Extract task text, specs, and relevant code into the agent prompt directly. Never tell an agent "read the plan file" or "check the spec at path X" -- that wastes their context window on navigation and risks misinterpretation. You already have the text; paste it.

**No parallel implementation agents (without worktrees):**

Implementation agents share state via git by default, so parallel dispatch causes overwrites. Use `isolation: "worktree"` to give each agent its own copy. Without worktrees, dispatch implementation agents sequentially. Review, research, and analysis agents are always safe to parallelize (read-only).

**Context pollution -- fresh agents for failures:**

If a subagent fails a task, dispatch a fresh agent to fix it. Don't try to fix in the failed agent's session. The failed agent's context is polluted with wrong assumptions and dead-end investigations that bias subsequent attempts.

**Model selection by task complexity:**

| Task shape | Model |
|-----------|-------|
| 1-2 files, clear spec, mechanical | `model: "haiku"` |
| Multi-file integration, standard complexity | Default model |
| Architecture decisions, ambiguous scope, review | `model: "opus"` |

**Handoff protocol -- structured agent-to-agent transfers:**

When passing work between agents (leader→implementer, implementer→reviewer, reviewer→leader), include:
1. **Context**: what was done, relevant files, constraints discovered
2. **Deliverable**: specific output expected from the receiving agent
3. **Acceptance criteria**: how the receiving agent knows the work is correct

Copy the necessary context into the prompt directly. Never tell the next agent "read the previous agent's output" -- paste it. See [handoff-templates.md](./references/handoff-templates.md) for QA FAIL and Escalation Report formats.

**Standardize implementer status signals:**

Include these four statuses in every teammate prompt so they know the reporting format. Expect teammates to report one of:
- **DONE** -- task complete, all tests pass
- **DONE_WITH_CONCERNS** -- complete but flagging risks (include what and why)
- **BLOCKED** -- cannot proceed. Escalation: context problem -> provide and re-dispatch; needs more reasoning -> upgrade model; task too large -> split; plan wrong -> escalate to user
- **NEEDS_CONTEXT** -- missing information to start. Provide context before re-dispatching.

Never ignore an escalation or force the same agent to retry without changes.

**QA retry loop:**

Max 3 attempts per task. After each QA failure, pass structured feedback to the implementer using the [QA FAIL template](./references/handoff-templates.md). After 3 failures, mark the task as blocked, continue the pipeline (don't halt everything), and let final integration catch remaining issues. Counter resets when advancing to the next task.

---

## Best Practices

1. **Use meaningful names** - `security-reviewer`, not `worker-1`.
2. **Write clear prompts** - Tell workers exactly what to do and how to report results.
3. **Use task dependencies** - Let the system manage unblocking via `addBlockedBy`.
4. **Prefer `write` over `broadcast`** - Broadcast sends N messages for N teammates.
5. **Handle failures** - Workers have 5-minute heartbeat timeout. Crashed workers' tasks can be reclaimed.
6. **Check inboxes** - Workers send results to your inbox at `~/.claude/teams/{team}/inboxes/team-lead.json`.
7. **Post-integration verification** - After all agents return: check if agents edited overlapping files (especially with worktrees), review summaries for conflicting approaches, run full test suite, spot-check for systematic errors.

---

## Coordination Models

Two approaches to multi-agent coordination exist. Choose based on the work pattern:

| Aspect | Stateless (copy-paste outputs) | Stateful (file ownership + dependencies) |
|--------|-------------------------------|------------------------------------------|
| How agents share state | Leader copies full outputs between prompts | Agents read/write shared task files, claim ownership |
| Best for | Short pipelines, 2-3 agents, sequential handoffs | Parallel work, 4+ agents, complex dependency graphs |
| Failure mode | Context grows linearly with agent count | Concurrent modification conflicts |
| Mitigation | Summarize before passing (keep essentials, drop navigation) | Use worktrees or exclusive file ownership per agent |

For most work, start with stateless handoffs. Graduate to stateful coordination only when parallelism provides a real speedup and you have worktree isolation to prevent file conflicts.

## Verify

- All tasks in terminal state (completed or blocked)
- No orphaned teammates (`git worktree list` shows no stale entries)
- Overlapping file edits reviewed and merged
- Full test suite passes post-integration

## References

| Document | When to load | What it covers |
|----------|-------------|----------------|
| [agent-types.md](./references/agent-types.md) | Choosing which agent to spawn | Built-in and plugin agent types with examples |
| [teammate-operations.md](./references/teammate-operations.md) | Using TeammateTool for persistent agents | All 13 operations (spawnTeam, write, broadcast, requestShutdown, etc.) |
| [task-system.md](./references/task-system.md) | Managing work items and dependencies | TaskCreate, TaskList, TaskGet, TaskUpdate, file structure |
| [message-formats.md](./references/message-formats.md) | Sending structured messages between agents | All JSON message examples (regular, shutdown, idle, plan approval) |
| [orchestration-patterns.md](./references/orchestration-patterns.md) | Designing a multi-agent workflow | 6 patterns + 3 complete workflow examples |
| [spawn-backends.md](./references/spawn-backends.md) | Troubleshooting agent spawn issues | Backend comparison, auto-detection, in-process/tmux/iterm2 |
| [environment-config.md](./references/environment-config.md) | Configuring team environment | Environment variables and team config structure |
| [handoff-templates.md](./references/handoff-templates.md) | Passing work between agents | QA FAIL and Escalation Report formats |
