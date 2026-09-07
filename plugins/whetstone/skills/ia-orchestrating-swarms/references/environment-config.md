# Environment Variables & Team Config

> When to read: when configuring teammate environment, scoping inheritance, or debugging missing env-var propagation across spawned instances.

## Environment Variables

Enable teams with the documented setting `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. Inspect the installed runtime rather than depending on internal identity environment variables. Supply the assigned worker name explicitly in its prompt:

```javascript
Agent({
  name: "worker",
  subagent_type: "general-purpose",
  description: "Complete assigned work",
  prompt: "Your assigned name is worker. Report task results to team-lead through SendMessage."
})
```

## Team Config Structure

`~/.claude/teams/{team-name}/config.json`, using the runtime-provided session-derived name. Inspect it read-only; this illustrative layout is not a schema to pre-author or edit:

```json
{
  "name": "session-a1b2c3d",
  "description": "Working on feature X",
  "leadAgentId": "team-lead@session-a1b2c3d",
  "createdAt": 1706000000000,
  "members": [
    {
      "agentId": "team-lead@session-a1b2c3d",
      "name": "team-lead",
      "agentType": "team-lead",
      "color": "#4A90D9",
      "joinedAt": 1706000000000,
      "backendType": "in-process"
    },
    {
      "agentId": "worker-1@session-a1b2c3d",
      "name": "worker-1",
      "agentType": "Explore",
      "model": "haiku",
      "prompt": "Analyze the codebase structure...",
      "color": "#D94A4A",
      "planModeRequired": false,
      "joinedAt": 1706000001000,
      "tmuxPaneId": "in-process",
      "cwd": "<repo-root>",
      "backendType": "in-process"
    }
  ]
}
```

## Model Selection

Subagent model resolution order: per-invocation `model` parameter, then the agent's frontmatter `model` field, then the main conversation's model. `CLAUDE_CODE_SUBAGENT_MODEL` sits below all three as a default (Claude Code v2.1.251+); earlier versions had it override every other setting, including `model: inherit`. To force one model onto every subagent regardless of frontmatter or invocation, also set `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` (v2.1.257+). Setting the variable to `inherit` is equivalent to leaving it unset. Confirm the resolved model with `/tasks` while a subagent is running.

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Named agent launches as a subagent | Teams disabled or noninteractive session | Check the teams setting and session mode; use subagents when teams are unavailable |
| Agent not found | Stale or wrong recipient | Inspect the active roster or runtime config for current names |
| Agent type not found | Invalid subagent_type | Inspect available built-in and plugin-qualified types |

### Graceful shutdown sequence

1. Account for each worker's assigned work and evidence.
2. Request shutdown through `SendMessage` using the [active protocol](./teammate-operations.md).
3. Wait for acknowledgement or an observed stopped state; idle is not stopped.
4. Let the runtime manage session cleanup. Task records persist; worktree cleanup remains separately scoped.

### Handling crashed teammates

Inspect the returned error, worker state, and owned-file diff before reassigning work. Do not assume a fixed heartbeat timeout proves termination or releases ownership. Follow the bounded verify-and-continue recovery procedure in [worker-lifecycle.md](./worker-lifecycle.md), reconcile task ownership, and report any unknown worker state.

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
