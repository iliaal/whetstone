# scope and sweeps

## Scope Confirmation (Pre-Edit Gate)

This gate fires at task start, before the first edit. When a request uses ambiguous spatial scope ("migrate my project", "refactor the codebase", "update everywhere", "fix this across the app", "my code/repo/project"), inspect the repository to resolve the concrete scope before any Write or Edit. Imperative phrasing is not defined scope.

Run a breakdown command to surface the real blast radius:

```bash
rg -l 'pattern' | cut -d/ -f1 | sort | uniq -c | sort -rn   # files per top-level dir
rg -l 'pattern' | xargs dirname | sort -u                   # affected directories
```

When the request and repository structure identify one safe interpretation, state the assumption and proceed. If multiple interpretations materially change the result, present the breakdown and ask via AskUserQuestion (Claude Code; load with ToolSearch `select:AskUserQuestion` if not loaded) or request_user_input (Codex); fall back to numbered options in chat. Do not start editing until that material choice is resolved.

**When this applies**: any request whose scope could plausibly span more than one subsystem and cannot be resolved safely from the request and repository structure. For a request with explicit file paths or one clear repository-wide interpretation, skip the question.

## Sweep Completion

For tasks whose scope is *every* item in a set (a repo-wide rename, "migrate everywhere", audit every file, resolve all findings), the Gate Function proves a command passed, not that it ran over the whole set. Track coverage explicitly.

Enumerate the set into a ledger held outside version control (a session-scratch path where the harness provides one, otherwise any git-ignored local directory, never a tracked file), one row per item with an explicit disposition: `pending`, `done`, `excluded (reason)`, or `blocked (evidence)`. Completion requires zero `pending` and zero `blocked`; "I covered a lot of them" is not a disposition.

Two rules close the holes that make a ledger lie:
- Re-enumerate after any path move or rename, so items created or relocated mid-sweep enter coverage instead of falling outside the original list.
- Keep removed items in the ledger until explicitly accounted for; an item that silently disappears reads identically to one that was finished.

Never claim coverage the ledger does not show.
