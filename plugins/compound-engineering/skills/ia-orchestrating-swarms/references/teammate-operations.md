# TeammateTool Operations

## 1. spawnTeam - Create a Team

```javascript
Teammate({
  operation: "spawnTeam",
  team_name: "feature-auth",
  description: "Implementing OAuth2 authentication"
})
```

**Creates:**
- `~/.claude/teams/feature-auth/config.json`
- `~/.claude/tasks/feature-auth/` directory
- You become the team leader

## 2. discoverTeams - List Available Teams

```javascript
Teammate({ operation: "discoverTeams" })
```

**Returns:** List of teams you can join (not already a member of)

## 3. requestJoin - Request to Join Team

```javascript
Teammate({
  operation: "requestJoin",
  team_name: "feature-auth",
  proposed_name: "helper",
  capabilities: "I can help with code review and testing"
})
```

## 4. approveJoin - Accept Join Request (Leader Only)

When you receive a `join_request` message:
```json
{"type": "join_request", "proposedName": "helper", "requestId": "join-123", ...}
```

Approve it:
```javascript
Teammate({
  operation: "approveJoin",
  target_agent_id: "helper",
  request_id: "join-123"
})
```

## 5. rejectJoin - Decline Join Request (Leader Only)

```javascript
Teammate({
  operation: "rejectJoin",
  target_agent_id: "helper",
  request_id: "join-123",
  reason: "Team is at capacity"
})
```

## 6. write - Message One Teammate

```javascript
Teammate({
  operation: "write",
  target_agent_id: "security-reviewer",
  value: "Please prioritize the authentication module. The deadline is tomorrow."
})
```

**Important for teammates:** Your text output is NOT visible to the team. You MUST use `write` to communicate.

## 7. broadcast - Message ALL Teammates

```javascript
Teammate({
  operation: "broadcast",
  name: "team-lead",  // Your name
  value: "Status check: Please report your progress"
})
```

**WARNING:** Broadcasting is expensive - sends N separate messages for N teammates. Prefer `write` to specific teammates.

**When to broadcast:**
- Critical issues requiring immediate attention
- Major announcements affecting everyone

**When NOT to broadcast:**
- Responding to one teammate
- Normal back-and-forth
- Information relevant to only some teammates

## 8. requestShutdown - Ask Teammate to Exit (Leader Only)

```javascript
Teammate({
  operation: "requestShutdown",
  target_agent_id: "security-reviewer",
  reason: "All tasks complete, wrapping up"
})
```

## 9. approveShutdown - Accept Shutdown (Teammate Only)

When you receive a `shutdown_request` message:
```json
{"type": "shutdown_request", "requestId": "shutdown-123", "from": "team-lead", "reason": "Done"}
```

**MUST** call:
```javascript
Teammate({
  operation: "approveShutdown",
  request_id: "shutdown-123"
})
```

This sends confirmation and terminates your process.

## 10. rejectShutdown - Decline Shutdown (Teammate Only)

```javascript
Teammate({
  operation: "rejectShutdown",
  request_id: "shutdown-123",
  reason: "Still working on task #3, need 5 more minutes"
})
```

## 11. approvePlan - Approve Teammate's Plan (Leader Only)

When teammate with `plan_mode_required` sends a plan:
```json
{"type": "plan_approval_request", "from": "architect", "requestId": "plan-456", ...}
```

Approve:
```javascript
Teammate({
  operation: "approvePlan",
  target_agent_id: "architect",
  request_id: "plan-456"
})
```

## 12. rejectPlan - Reject Plan with Feedback (Leader Only)

```javascript
Teammate({
  operation: "rejectPlan",
  target_agent_id: "architect",
  request_id: "plan-456",
  feedback: "Please add error handling for the API calls and consider rate limiting"
})
```

## 13. cleanup - Remove Team Resources

```javascript
Teammate({ operation: "cleanup" })
```

**Removes:**
- `~/.claude/teams/{team-name}/` directory
- `~/.claude/tasks/{team-name}/` directory

**IMPORTANT:** Will fail if teammates are still active. Use `requestShutdown` first.
