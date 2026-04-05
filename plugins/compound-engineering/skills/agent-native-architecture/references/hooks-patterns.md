# Hooks Patterns for Agent-Native Applications

Hooks intercept agent lifecycle events to enforce policy, inject context, and add side effects without modifying agent logic. This reference covers Claude Code hook patterns applicable to agent-native architectures.

## Hook Event Coverage

27 total hook events exist, but agent frontmatter hooks only support 6:

| Event | Fires in agent context | Decision control |
|-------|----------------------|------------------|
| **PreToolUse** | Yes | `permissionDecision`: allow, deny, ask, defer |
| **PostToolUse** | Yes | None (observe only) |
| **PermissionRequest** | Yes | `decision.behavior` |
| **PostToolUseFailure** | Yes | None (observe only) |
| **Stop** | Yes (received as SubagentStop) | `decision: block` to prevent stopping |
| **SubagentStop** | Yes | `decision: block` to prevent stopping |

SessionStart, SessionEnd, UserPromptSubmit, and all other events do **not** fire in agent context. Design accordingly: any logic that depends on session lifecycle or prompt modification must live in the parent orchestrator, not in agent-level hooks.

## Decision Control Patterns

### PreToolUse: Gate Tool Execution

Return a `permissionDecision` to control whether a tool call proceeds:

- **allow** -- bypass permission checks, let the call through
- **deny** -- block the call silently (agent sees denial, user does not approve)
- **ask** -- escalate to user confirmation
- **defer** -- fall through to the next hook or default behavior

Use PreToolUse to enforce invariants: prevent writes to protected paths, require confirmation for destructive operations, or inject validation before specific tools run.

### PermissionRequest: Override Permission UI

Return `decision.behavior` to control how permission prompts resolve. Useful for auto-approving known-safe operations in CI/automation contexts while preserving interactive approval in development.

### Stop / SubagentStop: Prevent Premature Completion

Return `decision: block` to prevent the agent from stopping. Apply this when an agent declares completion but mandatory verification steps remain (tests not run, checklist items unchecked, required outputs missing).

### UserPromptSubmit: Modify Prompts Before Processing

Available only in the parent context (not inside agents). Return a modified `prompt` field to inject context, rewrite instructions, or append constraints before the model sees the prompt.

## MCP Tool Matchers

Target specific MCP tools using regex patterns in the `matcher` field:

```json
{
  "hook": "PreToolUse",
  "matcher": "mcp__memory__.*",
  "command": "./hooks/guard-memory-writes.sh"
}
```

Common patterns:

| Pattern | Targets |
|---------|---------|
| `mcp__memory__.*` | All tools from the memory MCP server |
| `mcp__.*__write.*` | Any write tool from any MCP server |
| `mcp__github__create_.*` | All create operations on the GitHub server |
| `mcp__db__execute_query` | A specific tool on a specific server |

Regex matchers enable policy enforcement across MCP servers without enumerating every tool. Combine with PreToolUse `deny` to create a security boundary, or with `ask` to require human approval for specific operations.

## Two-Tier Configuration Strategy

Separate shared policy from personal overrides:

**Shared config** (committed to repo):
`.claude/hooks/config/hooks-config.json`

Contains team-wide policy: approval gates for destructive tools, audit logging, security boundaries. Committed and version-controlled so all team members inherit the same governance.

**Personal overrides** (git-ignored):
`.claude/hooks/config/hooks-config.local.json`

Individual toggles: disable noisy hooks during focused work, add personal notification hooks, override thresholds. Add to `.gitignore` so personal preferences never pollute the shared config.

**Per-hook disable toggles**: include an `enabled` field in each hook entry. Quick suppression without removing configuration -- flip the toggle, don't delete the block. Restoring a disabled hook is a one-character change instead of reconstructing the config.

## Async Hooks

For non-blocking side effects that should not slow the agent loop:

```json
{
  "hook": "PostToolUse",
  "matcher": ".*",
  "command": "./hooks/audit-log.sh",
  "async": true
}
```

Set `async: true` for logging, notifications, metrics collection, or any hook where the agent does not need the result before proceeding.

**asyncRewake**: for async hooks that should wake the model on failure. Use this when the side effect is best-effort but failures need visibility -- a logging hook that fails silently is fine, but a compliance audit hook that fails should surface the error.

## Architectural Implications

**Agent-level hooks are limited by design.** The 6 supported events cover tool execution and completion gating -- the two points where an agent interacts with the outside world. Session lifecycle and prompt modification are orchestrator concerns, not agent concerns. This aligns with the agent-native principle of granularity: agents handle execution, orchestrators handle coordination.

**Hooks replace hardcoded governance.** Instead of encoding approval logic in tool implementations, declare it in hook configuration. This keeps tools as primitives (principle of granularity) while governance becomes a composable layer (principle of composability). Adding a new approval gate means adding a hook entry, not modifying tool code.

**MCP matchers enable capability-based security.** Rather than trusting all tools equally, define security tiers via matcher patterns. Read-only tools auto-approve; write tools require confirmation; delete tools require explicit human approval. The security policy lives in configuration, not in each tool's implementation.
