# Hooks Patterns for Agent-Native Applications

Hooks intercept agent lifecycle events to enforce policy, inject context, and add side effects without modifying agent logic. This reference covers Claude Code hook patterns applicable to agent-native architectures.

## Hook Event Coverage

All 33 Claude Code hook events are declarable in agent frontmatter -- there is no reduced subset. The docs single out three as what matters most for subagent work, because those are the events tool execution and completion gating actually exercise:

| Event | Fires in agent context | Decision control |
|-------|----------------------|------------------|
| **PreToolUse** | Yes | `permissionDecision`: allow, deny, ask, defer |
| **PostToolUse** | Yes | None (observe only) |
| **PermissionRequest** | Yes | `decision.behavior` |
| **PostToolUseFailure** | Yes | None (observe only) |
| **PermissionDenied** | Yes | `retry: true` -- lets the model retry the denied call; ignored when the classifier gave no verdict |
| **Stop** | Yes -- converted to `SubagentStop` when the agent runs as a subagent | `decision: block` to prevent stopping |
| **SubagentStop** | Yes | `decision: block` to prevent stopping |

A frontmatter `Stop` hook is rewritten to `SubagentStop` whenever the agent is invoked as a subagent (via the Agent tool or an @-mention). The same frontmatter hooks fire unmodified when that agent instead runs as the main session via `claude --agent <name>` -- a hook written for one context stays live in the other, so it needs to tolerate both. Project-level agent frontmatter hooks require workspace trust (Claude Code v2.1.218+); an untrusted workspace skips them without error.

## Decision Control Patterns

### PreToolUse: Gate Tool Execution

Return a `permissionDecision` to control whether a tool call proceeds:

- **allow** -- bypass permission checks, let the call through
- **deny** -- block the call silently (agent sees denial, user does not approve)
- **ask** -- escalate to user confirmation
- **defer** -- fall through to the next hook or default behavior

Use PreToolUse to enforce invariants: prevent writes to protected paths, require confirmation for destructive operations, or inject validation before specific tools run.

**The decision must nest under `hookSpecificOutput`, with `hookEventName`.** A flat top-level `permissionDecision` is ignored without error, so a `deny` hook written that way allows every call it was installed to block:

```json
{ "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "path is under a protected prefix" } }
```

Parse the incoming event and build this response with a real JSON tool (`jq`), never `grep` plus `printf` interpolation. A grep-based field extractor truncates on an escaped quote, and an interpolated response silently malforms on a path containing a quote or newline -- in both cases the block evaporates. Treat an unparseable payload as deny, not as allow: a gate whose failure mode is "permit" is not a gate. Verify by asserting the hook denies a call it should deny, since a hook that returns nothing looks identical to a hook that approved.

That fail-closed rule covers the gate's decision logic, not its bookkeeping. A hook that tracks per-session state (a first-touch marker, a cache file, a state directory) hits a separate failure mode when that storage is unwritable or corrupt -- failing closed there blocks every later call in the session with no way to ever record "already checked", which deadlocks the gate rather than protecting it. Fail open on bookkeeping failures instead, and name the broken path or variable in a stderr warning so the gap is visible rather than silent.

Expose narrow-scope overrides separately from the full kill switch: an env var that disables one sub-check (e.g. a routine-command gate) and a path-glob exemption list, distinct from the variable that turns the entire hook off. That lets a user silence one noisy check without disabling the load-bearing destructive-command gate alongside it.

### PermissionRequest: Override Permission UI

Return `decision.behavior` to control how permission prompts resolve. Useful for auto-approving known-safe operations in CI/automation contexts while preserving interactive approval in development.

### Stop / SubagentStop: Prevent Premature Completion

Return `decision: block` to prevent the agent from stopping. Apply this when an agent declares completion but mandatory verification steps remain (tests not run, checklist items unchecked, required outputs missing).

### UserPromptSubmit: Modify Prompts Before Processing

Declarable in frontmatter like every event, but it fires only when the agent runs as the main session (`claude --agent <name>`); a spawned subagent receives no user prompt, so the hook is inert there. Return a modified `prompt` field to inject context, rewrite instructions, or append constraints before the model sees the prompt.

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

**Matcher semantics.** `"*"`, `""`, or an omitted `matcher` field all match every tool call. Anything else is a JavaScript regex tested unanchored via `RegExp.prototype.test`, so `mcp__memory` (no `.*`) still matches `mcp__memory__write` -- anchor deliberately, or leave the field off when a catch-all is actually intended.

**The `if` field.** Hook entries also accept an `if` field using permission-rule syntax (`"Bash(git *)"`, `"Edit(*.ts)"`) to scope a hook past what the matcher alone can express. Only tool-shaped events evaluate it -- PreToolUse, PostToolUse, PostToolUseFailure, PermissionRequest, PermissionDenied. An `if` attached to a non-tool event (Stop, SessionStart) is inert.

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

**Tool execution and completion gating carry the governance weight.** PreToolUse, PostToolUse, and Stop/SubagentStop are the events agent-native architectures lean on -- the points where an agent touches the outside world and where it claims done. This aligns with the agent-native principle of granularity: agents handle execution, orchestrators handle coordination.

**Hooks replace hardcoded governance.** Instead of encoding approval logic in tool implementations, declare it in hook configuration. This keeps tools as primitives (principle of granularity) while governance becomes a composable layer (principle of composability). Adding a new approval gate means adding a hook entry, not modifying tool code.

**MCP matchers enable capability-based security.** Rather than trusting all tools equally, define security tiers via matcher patterns. Read-only tools auto-approve; write tools require confirmation; delete tools require explicit human approval. The security policy lives in configuration, not in each tool's implementation.
