# Claude Code teammate operations

> When to read: when spawning persistent teammates, sending messages, handling shutdown, or distinguishing automatic protocol transitions from review decisions.

Use the installed session's tool schemas. The examples below match Claude Code 2.1.263's `Agent` and `SendMessage` surface; older runtimes need their own exposed schema. See [official agent-team behavior](https://code.claude.com/docs/en/agent-teams) and [tool reference](https://code.claude.com/docs/en/tools-reference).

## Start teammates

Enable `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in an interactive Claude Code session. Named agents then launch as teammates:

```javascript
Agent({
  name: "auth-worker",
  subagent_type: "general-purpose",
  description: "Implement authentication",
  prompt: "Implement the assigned authentication unit within its supplied file ownership and acceptance criteria. Report evidence to team-lead.",
  run_in_background: true
})
```

No explicit team creation is required. The runtime derives the team name from the session; omit the ignored `team_name` argument. Noninteractive `-p` sessions use subagents instead.

## Discover current members

Read the runtime-provided roster or the actual session's team config for member names. Use `ListAgents` only when exposed. Do not invent team discovery, join-request, or join-approval operations; spawn the needed teammate from the current session instead. Do not edit team config to add a member.

## Message one teammate

```javascript
SendMessage({
  to: "security-reviewer",
  message: "Prioritize the authentication module and report verified findings or explicitly no findings.",
  summary: "Prioritize authentication review"
})
```

Use the recipient's actual name or returned agent ID. Teammates send results to the lead through `SendMessage`; finishing a turn or becoming idle is not proof that a report was delivered.

## Notify multiple teammates

Send one message per intended recipient. There is no separate broadcast operation in this schema.

```javascript
SendMessage({ to: "auth-worker", message: "Pause edits: the shared authentication interface is changing." })
SendMessage({ to: "test-worker", message: "Pause edits: the shared authentication interface is changing." })
```

Multiple messages cost more than one. Notify everyone only for a coordination change that affects everyone; otherwise send directly to the affected worker.

## Request shutdown

When the assigned work is accounted for and shutdown is authorized:

```javascript
SendMessage({
  to: "security-reviewer",
  message: { type: "shutdown_request", reason: "Assigned review is complete" }
})
```

Wait for the actual acknowledgement or stopped state. An idle notification is not shutdown.

## Accept or reject a shutdown request

Use the request identifier received from the runtime, not an invented ID:

```javascript
SendMessage({
  to: "team-lead",
  message: { type: "shutdown_response", request_id: "received-request-id", approve: true }
})
```

Approving terminates the teammate. If work remains, reject with the reason:

```javascript
SendMessage({
  to: "team-lead",
  message: {
    type: "shutdown_response",
    request_id: "received-request-id",
    approve: false,
    reason: "The assigned verification is still running"
  }
})
```

## Plan-mode transitions and review

Current Claude Code automatically approves teammate plan requests; that transition is not evidence of a reviewed design or user authorization. For a real review gate, dispatch a read-only planner that returns a plan and stops. Review the artifact against explicit criteria, resolve material decisions, then dispatch implementation within existing authority. Do not depend on a teammate's automatic plan-mode exit to enforce this gate.

If an older active runtime actually delivers a plan request requiring a response, its `SendMessage` schema may expose the legacy response:

```javascript
SendMessage({
  to: "architect",
  message: {
    type: "plan_approval_response",
    request_id: "received-request-id",
    approve: false,
    feedback: "Add failure recovery and rate limiting before implementation"
  }
})
```

Use `approve: true` only for an actual reviewed plan within the caller's authority. A protocol response cannot grant permissions the user has not supplied.

## Session cleanup

The runtime cleans up team config when the session ends; the task list persists for resumption. Do not call removed team-creation/deletion tools or delete the task store as cleanup.

Account for all assigned work and teammate states before ending orchestration. Worktree cleanup is separate: verify integration and preserve dirty or unrelated worktrees under the main skill's ownership rules.
