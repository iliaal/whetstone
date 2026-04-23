# Orchestrating Swarms — Quick Reference

Code snippets for the common spawn/message/task/shutdown operations. Load when setting up a specific coordination pattern — the decision logic lives in the main SKILL.md.

## Spawn Team + Teammate

```javascript
Teammate({ operation: "spawnTeam", team_name: "my-team" })
Task({ team_name: "my-team", name: "worker", subagent_type: "general-purpose",
       prompt: "...", run_in_background: true })
```

## Message a Teammate

```javascript
Teammate({ operation: "write", target_agent_id: "worker-1", value: "..." })
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
Teammate({ operation: "requestShutdown", target_agent_id: "worker-1" })
// Wait for shutdown_approved message...
Teammate({ operation: "cleanup" })
```
