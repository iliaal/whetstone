# CLI as an Agent Interface

> When to read: designing or reviewing a command-line tool that agents invoke through a shell tool, as opposed to an MCP server. Agents call the same binary humans do, but consume it differently: they parse output, branch on exit codes, and pay tokens for every byte the tool prints.

## Three-channel contract

Assign one job to each channel and never mix them:

- **stdout** carries the result only, as machine-parseable JSON (one document, or one object per line for streams). No banners, progress, or prompts.
- **stderr** carries human diagnostics: progress, warnings, hints. An agent may ignore it without losing the result.
- **Exit codes** carry the outcome class. Reserve distinct codes for success, usage error, not-found, permission or auth failure, and transient failure, and document them. An agent decides whether to retry, ask, or stop from the code before it parses anything.

Write errors to stdout as well when the tool fails, in the same JSON shape (`{"error": {"code": "...", "message": "...", "hint": "..."}}`), so the parser has one path.

## Output mode detection

Detect a TTY on stdout. Interactive terminal: human formatting, color, tables. Non-interactive: JSON, no color, no spinners. Make both overridable: `--format json|text` wins over detection, and honor `NO_COLOR` for the human mode. An agent that must pass `--json` to every call will forget once; the default has to be safe for it.

## Progressive self-description

Top-level `--help` lists resources and actions in one screen; the agent pays that cost on every discovery call, so keep it short. Expose the full typed contract behind a separate `schema <resource.action>` subcommand that returns argument types, constraints, and the response shape as JSON. Dumping the schema into `--help` is the anti-pattern: every invocation carries the whole surface into context, and the agent still cannot parse it reliably.

## A `meta` block in every response

Include the schema version, the tool version, and any deprecation notices alongside the data:

```json
{ "data": { "id": "inv_204", "status": "paid" },
  "meta": { "schema": "2.1", "tool": "billctl 4.3.0",
            "deprecated": ["--customer is replaced by --account"] } }
```

Agents cache what they learned from `schema` earlier in a session or in memory. Without `meta`, a schema change looks like a tool bug; with it, the agent detects drift and re-reads the schema.

## Graduated safety for destructive commands

Tier destructive actions: dry-run by default, `--yes` to execute, `--force` for anything that bypasses a safeguard. Print what would change in the dry run in the same JSON shape as the real result. These tiers protect against an agent that misread intent; they do not protect against one instructed by injected content, and they cannot bound damage from a bug in the tool itself. Pair them with OS-level sandboxing (containers, restricted users, read-only mounts, network policy) and with the harness permission layer; the flags are a usability tier, not a security boundary.
