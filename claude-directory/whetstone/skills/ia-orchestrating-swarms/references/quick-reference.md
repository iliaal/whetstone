# Orchestrating Swarms: Quick Reference

Code snippets for the common spawn/message/task/shutdown operations. Load when setting up a specific coordination pattern; the decision logic lives in the main SKILL.md. These are Claude Code examples: inspect active schemas and use [teammate-operations.md](./teammate-operations.md) for prerequisites and lifecycle details. No explicit team creation or deletion is needed.

## Spawn a Subagent (short-lived, returns a result)

```javascript
Agent({ subagent_type: "Explore", description: "Find auth files", prompt: "..." })
```

## Parallel Fan-Out (one message, multiple tool uses)

```javascript
Agent({ subagent_type: "whetstone:ia-security-sentinel", description: "Review security", prompt: "Independently review the supplied change for security; return evidence or no findings." })
Agent({ subagent_type: "whetstone:ia-performance-oracle", description: "Review performance", prompt: "Independently review the supplied change for performance; return evidence or no findings." })
Agent({ subagent_type: "whetstone:ia-architecture-strategist", description: "Review architecture", prompt: "Independently review the supplied change against its architecture constraints; return evidence or no findings." })
```

## Spawn a teammate (interactive session with agent teams enabled)

```javascript
Agent({ name: "worker", subagent_type: "general-purpose", description: "Complete assigned unit",
       prompt: "...", run_in_background: true })
```

## Message a Teammate

```javascript
SendMessage({ to: "worker-1", message: "..." })
```

## Create Task Pipeline

```javascript
TaskCreate({ subject: "Step 1", description: "...", activeForm: "Working..." })
TaskCreate({ subject: "Step 2", description: "...", activeForm: "Working..." })
TaskUpdate({ taskId: "2", addBlockedBy: ["1"] })  // #2 waits for #1
```

## Claim and Complete Tasks (as teammate)

```javascript
TaskUpdate({ taskId: "1", owner: "my-name", status: "in_progress" })
// ... do work ...
TaskUpdate({ taskId: "1", status: "completed" })
```

## Shutdown Team

```javascript
SendMessage({ to: "worker-1", message: { type: "shutdown_request", reason: "Assigned work complete" } })
// Wait for shutdown_approved message...
```

Session cleanup is automatic; retain task records and handle owned worktrees separately.
