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

### Parallel Fan-Out (for independent work)

When dispatching multiple read-only or worktree-isolated agents whose work is independent, issue all Task calls in a SINGLE assistant message. Sequential dispatch across separate messages serializes what should run concurrently. Opus 4.7 does not parallelize by default -- state it explicitly.

```javascript
// Correct: one message, multiple Task tool uses
Task({ subagent_type: "security-sentinel", ... })
Task({ subagent_type: "performance-oracle", ... })
Task({ subagent_type: "architecture-strategist", ... })
```

Sequential dispatch (each Task in its own message, waiting on the previous to return) is a serialization bug, not a coordination pattern. If agents truly depend on each other's output, that is a pipeline -- see Coordination Models below.

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

**Task description template (for every dispatched task):**

Every task prompt must include these fields to prevent integration failures:
- **Objective**: what to accomplish (one sentence)
- **Owned Files**: files this agent creates or modifies (exclusive -- no file assigned to multiple agents)
- **Interface Contracts**: what to import from other agents' work, what to export for downstream agents
- **Acceptance Criteria**: how the agent knows the task is correct
- **Out of Scope**: what NOT to touch, even if it looks related

Cardinal rule: one owner per file. When files must be shared, designate a single owner; other agents send change requests, owner applies sequentially. If an upstream dependency isn't ready yet, write a stub/mock so downstream work can continue unblocked.

**No parallel implementation agents (without worktrees):**

Implementation agents share state via git by default, so parallel dispatch causes overwrites. Use `isolation: "worktree"` to give each agent its own copy. Without worktrees, dispatch implementation agents sequentially. Review, research, and analysis agents are always safe to parallelize (read-only).

**Pre-dispatch file-intersection check** -- operationalize the one-owner-per-file rule with a runnable safety gate before every parallel dispatch:

1. Collect each unit's declared Owned Files / Test Paths / Modify Paths from its task spec.
2. Build a `{file → unit}` map. If any file appears under more than one unit, the dispatch is unsafe.
3. On overlap: either downgrade to serial (log the overlap and the reason), or assign worktree isolation (`isolation: "worktree"` per agent), or rewrite unit boundaries so files become exclusive.
4. Even with no declared overlap, include this constraint verbatim in every parallel-dispatch prompt: *"Do not run `git add`, `git commit`, or the project's test suite while other parallel agents are active -- you'd race on the git index or thrash the test cache. Stage changes for the orchestrator to commit after integration."*

The intersection check catches silent conflicts the controller misses at plan time; the dispatch-prompt constraint catches them when a unit's file list was incomplete.

**Preset team compositions:** Start from a named preset before designing a custom team. See [team-compositions.md](./references/team-compositions.md) for the full table (Review / Debug / Feature / Fullstack / Migration / Security / Research), the cardinal `subagent_type` rule (read-only agents cannot implement), and custom-team guidelines. Use the smallest preset that covers all required dimensions — overlap between reviewers is a sizing signal to redefine focus areas, not add more agents.

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

The controller reads all tasks from the plan upfront and provides full task text directly to subagents. Never make subagents read plan files themselves -- they waste tokens navigating, may read different versions, and inherit unclear context. Paste the task content into the prompt. See [handoff-templates.md](./references/handoff-templates.md) for QA FAIL and Escalation Report formats.

**Standardize implementer status signals:**

Include these four statuses in every teammate prompt so they know the reporting format. Expect teammates to report one of:
- **DONE** -- task complete, all tests pass
- **DONE_WITH_CONCERNS** -- complete but flagging risks (include what and why)
- **BLOCKED** -- cannot proceed. See BLOCKED triage decision tree below.
- **NEEDS_CONTEXT** -- missing information to start or continue. Provide context before re-dispatching.

**BLOCKED triage decision tree** -- when a teammate reports BLOCKED, classify the root cause before acting. Never retry the same prompt on the same model without changing a variable.

| Root cause | Signal | Response |
|-----------|--------|----------|
| Missing context | Agent asked for a file, spec, or decision it needed | Provide the missing context, re-dispatch same agent |
| Reasoning ceiling | Agent attempted, got stuck on a subtlety it cannot resolve | Escalate model (haiku → sonnet → opus) and re-dispatch |
| Task too large | Agent made partial progress but hit token/complexity limits | Split into smaller tasks with explicit interface contracts |
| Spec wrong | Agent surfaces a contradiction in the plan or a missing requirement | Escalate to the user -- do not re-dispatch |

Never ignore an escalation. Never force the same agent to retry without changing at least one variable (context, model, or task scope).

**Two-stage review gate on subagent outputs:**

Verify spec compliance first: does the output match what was requested? Only then evaluate quality. A beautifully written solution to the wrong problem is still wrong. Structure review as two explicit passes -- pass 1 rejects on spec mismatch without reading further, pass 2 assesses correctness and quality on spec-compliant outputs.

**QA retry loop:**

Max 3 attempts per task. After each QA failure, pass structured feedback to the implementer using the [QA FAIL template](./references/handoff-templates.md). After 3 failures, mark the task as blocked, continue the pipeline (don't halt everything), and let final integration catch remaining issues. Counter resets when advancing to the next task.

---

## Integration Rules

**Post-integration verification** -- after all agents return: check overlapping file edits, review for conflicting approaches, run full test suite.

**Spawned-session behavior** -- when a skill runs inside an orchestrated pipeline (as a subagent, not user-invoked), suppress interactive prompts: do not use AskUserQuestion, auto-choose the conservative/safe default, skip upgrade checks and telemetry. Focus on completing the task and reporting results via prose output. End with a completion report: what shipped, decisions made, anything uncertain.

---

## Context Carry-Forward

After each turn, five strategies exist for moving context forward: Continue, Rewind, `/compact`, Subagent, `/clear`+brief. Choose deliberately — the default "Continue" is rarely best, and Rewind is strictly better than "correcting in place" after a failed attempt. See [context-carry-forward.md](./references/context-carry-forward.md) for the full decision table and rationale.

## Coordination Models

Two approaches to multi-agent coordination exist. Choose based on the work pattern:

| Aspect | Stateless (copy-paste outputs) | Stateful (file ownership + dependencies) |
|--------|-------------------------------|------------------------------------------|
| How agents share state | Leader copies full outputs between prompts | Agents read/write shared task files, claim ownership |
| Best for | Short pipelines, 2-3 agents, sequential handoffs | Parallel work, 4+ agents, complex dependency graphs |
| Failure mode | Context grows linearly with agent count | Concurrent modification conflicts |
| Mitigation | Summarize before passing (keep essentials, drop navigation) | Use worktrees or exclusive file ownership per agent |

For most work, start with stateless handoffs. Graduate to stateful coordination only when parallelism provides a real speedup and you have worktree isolation to prevent file conflicts.

---

## Anti-Sycophancy Patterns

Multi-agent swarms can converge on wrong answers through groupthink. These patterns prevent agents from anchoring on each other's outputs.

**Cold-start agent isolation:**

Each agent in a swarm receives only the task description and fresh context. No session history, no prior agent outputs until an explicit synthesis phase. When running parallel reviewers or evaluators, the orchestrator holds all outputs until every agent has submitted independently, then passes the collected results to a synthesis agent.

**Fresh instances on every re-dispatch round:**

When re-running reviewers across iterations (QA retry loop, re-review after fixes, multi-round evaluation), spawn a completely fresh agent each round -- never reuse the same instance. Reviewers carrying memory from a prior round anchor on their earlier verdicts and miss regressions introduced by the fix. A reviewer who said "this is fine" in round 1 will rationalize back toward that verdict in round 2 even when a bad change has landed. Cold-start applies to every round, not just the first.

**Label randomization for judge panels:**

When multiple candidates are evaluated (e.g., parallel implementations, competing approaches), judges see randomized labels -- X/Y/Z, not A/B or "original"/"improved." Re-shuffle labels each evaluation round. This prevents anchoring on position ("A is always the baseline") or naming ("the synthesis must be better").

**Convergence detection:**

Track an incumbent (current best candidate). If the same candidate wins N consecutive evaluation rounds (default: 3), stop iterating -- the swarm has converged. This prevents infinite iteration on subjective tasks where no clear winner emerges and additional rounds just burn tokens.

---

## Resilience Patterns

Swarm failures are inevitable. Contain blast radius and recover partial value rather than discarding everything.

**Cascade prevention:**

Set timeout boundaries per agent. If one agent fails or hangs, do not let it cascade into abandoning the entire swarm's work. The orchestrator treats each agent as independently failable -- other agents continue their work unaffected. Terminate unresponsive agents after the timeout rather than waiting indefinitely.

Apply circuit-breaker logic to agent types: after N consecutive failures from the same agent type, stop dispatching to it and route to an alternative (different model, different decomposition). Apply bulkhead isolation: a failing agent type cannot exhaust the shared task queue or block other agent types from proceeding.

**Recovery strategy:**

When an agent fails, classify the failure before acting:
- **Retry** -- transient errors (network timeout, rate limit). Re-dispatch the same task.
- **Reassign** -- agent-specific issue (context pollution, wrong model for task complexity). Dispatch a fresh agent, optionally with a different model.
- **Escalate** -- systemic problem (bad spec, missing dependency, impossible constraint). Surface to the orchestrator or user with an [Escalation Report](./references/handoff-templates.md).

For agent-reported `BLOCKED` status specifically (as opposed to crashes or timeouts), use the BLOCKED triage decision tree under "Dispatch Discipline" above — it maps the four BLOCKED root causes (missing context / reasoning ceiling / task too large / spec wrong) to concrete responses.

Never retry blindly. Repeating the same prompt in the same conditions produces the same failure.

**Mid-pipeline compensation:**

When an agent fails mid-pipeline after earlier agents have already written files or made changes, classify whether those earlier effects are reversible before deciding the recovery path. If reversible (file writes, uncommitted changes), revert and retry the pipeline segment. If irreversible (committed code, external API calls, database writes), compensate rather than retry -- apply a corrective action that accounts for the partial state. Never retry blindly when earlier stages have produced side effects.

**Post-failure synthesis:**

Even partial results from a failed swarm run have value. When some agents succeed and others fail, collect and present the successful outputs rather than discarding everything. Mark failed tasks as incomplete in the synthesis so downstream consumers know which areas lack coverage.

## Verify

- All tasks in terminal state (completed or blocked)
- No orphaned teammates (`git worktree list` shows no stale entries)
- Overlapping file edits reviewed and merged
- Full test suite passes post-integration

## References

| Document | When to load | What it covers |
|----------|-------------|----------------|
| [team-compositions.md](./references/team-compositions.md) | Sizing a team or choosing a preset | 7 preset compositions, subagent_type cardinal rule, custom-team guidelines |
| [agent-types.md](./references/agent-types.md) | Choosing which agent to spawn | Built-in and plugin agent types with examples |
| [teammate-operations.md](./references/teammate-operations.md) | Using TeammateTool for persistent agents | All 13 operations (spawnTeam, write, broadcast, requestShutdown, etc.) |
| [task-system.md](./references/task-system.md) | Managing work items and dependencies | TaskCreate, TaskList, TaskGet, TaskUpdate, file structure |
| [message-formats.md](./references/message-formats.md) | Sending structured messages between agents | All JSON message examples (regular, shutdown, idle, plan approval) |
| [orchestration-patterns.md](./references/orchestration-patterns.md) | Designing a multi-agent workflow | 6 patterns + 3 complete workflow examples |
| [spawn-backends.md](./references/spawn-backends.md) | Troubleshooting agent spawn issues | Backend comparison, auto-detection, in-process/tmux/iterm2 |
| [environment-config.md](./references/environment-config.md) | Configuring team environment | Environment variables and team config structure |
| [handoff-templates.md](./references/handoff-templates.md) | Passing work between agents | QA FAIL and Escalation Report formats |
| [context-carry-forward.md](./references/context-carry-forward.md) | Long sessions with orchestrated subagents | Continue / Rewind / compact / Subagent / clear+brief decision table |
