---
name: resolve-pr
description: Resolve PR review comments with cluster analysis and parallel agents. Use when bulk-fixing PR comments after triage.
argument-hint: "[PR number or URL]"
---

# Resolve PR Comments

**PR:** #$ARGUMENTS

Resolve all unresolved PR review comments. If no PR number given, detect from current branch.

Use the `receiving-code-review` skill for how to handle each comment (verify before implementing, push back on incorrect suggestions).

## Phase 1: Fetch

Fetch unresolved review threads:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/commands/scripts/get-pr-comments PR_NUMBER
```

Returns only **unresolved, non-outdated** threads with file paths, line numbers, and comment bodies. Filter out bot comments (CI, linters, coverage).

If the script fails, fall back to:
```bash
gh pr view PR_NUMBER --json reviews,comments
gh api repos/{owner}/{repo}/pulls/PR_NUMBER/comments
```

## Phase 2: Cluster Analysis

When 3+ comments exist, analyze for thematic patterns before fixing individually:

| Theme | Signal |
|-------|--------|
| Error handling | Multiple comments about missing try/catch, unchecked returns, error paths |
| Validation | Input checking, type guards, boundary conditions |
| Security | Auth, injection, secrets exposure, access control |
| Naming/clarity | Variable names, function names, confusing logic |
| Testing | Missing tests, weak assertions, test quality |
| Architecture | Coupling, responsibility boundaries, abstraction levels |

**If a cluster has 3+ comments:** Fix the underlying pattern rather than addressing each comment individually. State the systemic fix and reference which comments it addresses.

**If comments span multiple review rounds:** Prior unresolved comments alongside new ones indicate the reviewer isn't satisfied with previous fixes. Prioritize those threads.

For fewer than 3 comments, skip clustering and resolve directly.

## Phase 3: Resolve (parallel)

Create a TodoWrite list grouped by severity:
- **Critical**: Logic bugs, security issues, broken functionality
- **Important**: Code quality, missing tests, architecture concerns
- **Minor**: Style, naming, convention fixes
- **Questions**: Clarifications to answer (not code changes)

Spawn a `pr-comment-resolver` agent for each item in parallel. For systemic clusters, spawn one agent for the cluster with all related comments in its prompt.

## Phase 4: Commit and Verify

- Group related changes into logical commits (one per concern, not per file)
- Commit message: `address review: <summary>`
- Resolve each thread:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/commands/scripts/resolve-pr-thread THREAD_ID
```

- Push to remote
- Re-fetch comments to confirm all resolved:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/commands/scripts/get-pr-comments PR_NUMBER
```

Should return empty. If threads remain, repeat from Phase 1.

Run `verification-before-completion` before reporting done.

## Scripts

- [scripts/get-pr-comments](scripts/get-pr-comments) - GraphQL query for unresolved review threads
- [scripts/resolve-pr-thread](scripts/resolve-pr-thread) - GraphQL mutation to resolve a thread by ID

## Success Criteria

- All unresolved review threads addressed
- Systemic patterns identified and fixed at the root (not comment-by-comment)
- Changes committed and pushed
- Threads resolved via GraphQL
- Empty result from get-pr-comments on verify
