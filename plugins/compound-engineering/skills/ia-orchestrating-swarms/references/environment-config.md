# Environment Variables & Team Config

## Environment Variables

Spawned teammates automatically receive these:

```bash
CLAUDE_CODE_TEAM_NAME="my-project"
CLAUDE_CODE_AGENT_ID="worker-1@my-project"
CLAUDE_CODE_AGENT_NAME="worker-1"
CLAUDE_CODE_AGENT_TYPE="Explore"
CLAUDE_CODE_AGENT_COLOR="#4A90D9"
CLAUDE_CODE_PLAN_MODE_REQUIRED="false"
CLAUDE_CODE_PARENT_SESSION_ID="session-xyz"
```

**Using in prompts:**
```javascript
Task({
  team_name: "my-project",
  name: "worker",
  subagent_type: "general-purpose",
  prompt: "Your name is $CLAUDE_CODE_AGENT_NAME. Use it when sending messages to team-lead."
})
```

## Team Config Structure

`~/.claude/teams/{team-name}/config.json`:

```json
{
  "name": "my-project",
  "description": "Working on feature X",
  "leadAgentId": "team-lead@my-project",
  "createdAt": 1706000000000,
  "members": [
    {
      "agentId": "team-lead@my-project",
      "name": "team-lead",
      "agentType": "team-lead",
      "color": "#4A90D9",
      "joinedAt": 1706000000000,
      "backendType": "in-process"
    },
    {
      "agentId": "worker-1@my-project",
      "name": "worker-1",
      "agentType": "Explore",
      "model": "haiku",
      "prompt": "Analyze the codebase structure...",
      "color": "#D94A4A",
      "planModeRequired": false,
      "joinedAt": 1706000001000,
      "tmuxPaneId": "in-process",
      "cwd": "/Users/me/project",
      "backendType": "in-process"
    }
  ]
}
```

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Cannot cleanup with active members" | Teammates still running | `requestShutdown` all teammates first, wait for approval |
| "Already leading a team" | Team already exists | `cleanup` first, or use different team name |
| "Agent not found" | Wrong teammate name | Check `config.json` for actual names |
| "Team does not exist" | No team created | Call `spawnTeam` first |
| "team_name is required" | Missing team context | Provide `team_name` parameter |
| "Agent type not found" | Invalid subagent_type | Check available agents with proper prefix |

### Graceful Shutdown Sequence

**Always follow this sequence:**

```javascript
// 1. Request shutdown for all teammates
Teammate({ operation: "requestShutdown", target_agent_id: "worker-1" })
Teammate({ operation: "requestShutdown", target_agent_id: "worker-2" })

// 2. Wait for shutdown approvals
// Check for {"type": "shutdown_approved", ...} messages

// 3. Verify no active members
// Read ~/.claude/teams/{team}/config.json

// 4. Only then cleanup
Teammate({ operation: "cleanup" })
```

### Handling Crashed Teammates

Teammates have a 5-minute heartbeat timeout. If a teammate crashes:

1. They'll be automatically marked as inactive after timeout
2. Their tasks remain in the task list
3. Another teammate can claim their tasks
4. Cleanup will work after timeout expires

### Debugging

```bash
# Check team config
cat ~/.claude/teams/{team}/config.json | jq '.members[] | {name, agentType, backendType}'

# Check teammate inboxes
cat ~/.claude/teams/{team}/inboxes/{agent}.json | jq '.'

# List all teams
ls ~/.claude/teams/

# Check task states
cat ~/.claude/tasks/{team}/*.json | jq '{id, subject, status, owner, blockedBy}'

# Watch for new messages
tail -f ~/.claude/teams/{team}/inboxes/team-lead.json
```
