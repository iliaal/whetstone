---
name: ia-resolve-pr
description: Resolve PR review comments with cluster analysis and parallel agents. Use when bulk-fixing PR comments after triage.
argument-hint: "[PR number or URL]"
---

# Resolve PR Comments

**PR:** #$ARGUMENTS

Resolve all unresolved PR review comments. If no PR number given, detect from current branch.

Use the `ia-receiving-code-review` skill for how to handle each comment (verify before implementing, push back on incorrect suggestions).

## Phase 1: Fetch

Fetch review threads:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/commands/scripts/get-pr-comments PR_NUMBER
```

Returns `{unresolved: [...threads], cross_invocation: {signal, resolved_threads}}`. The `unresolved` array carries non-outdated threads with file paths, line numbers, and comment bodies — fix work targets these. The `cross_invocation` block exists so Phase 2 clustering can require cross-round evidence: `signal` is true when both resolved and unresolved threads coexist on the PR (multi-round review), and `resolved_threads` lists the resolved thread paths/IDs for spatial-overlap precheck. Filter out bot comments (CI, linters, coverage) from `unresolved` before processing.

If the script fails, fall back to:
```bash
gh pr view PR_NUMBER --json reviews,comments
gh api repos/{owner}/{repo}/pulls/PR_NUMBER/comments
```

## Phase 2: Cluster Analysis

**Gate (skip clustering unless both pass):**
1. **Cross-round signal**: `cross_invocation.signal == true` — resolved threads exist alongside new ones. First-round reviews fail this gate; dispatch comments individually.
2. **Spatial-overlap precheck**: at least one unresolved thread shares an exact file path or directory subtree with a thread in `cross_invocation.resolved_threads`. Path comparison only, no LLM call. Skip this stage if `resolved_threads` lacks paths.

If either stage fails, dispatch comments individually (skip to Phase 3). Single-round same-theme groupings are intentionally not clustered: evidence is too thin and the false-positive rate is high. First-round "one helper would fix all of these" opportunities surface naturally as individual fixes; recurring reviewer feedback across rounds promotes them into cluster mode.

**If both gate stages pass**, analyze for thematic patterns spanning new and previously-resolved threads:

| Theme | Signal |
|-------|--------|
| Error handling | Multiple comments about missing try/catch, unchecked returns, error paths |
| Validation | Input checking, boundary conditions, runtime range/format checks |
| Type safety | Type guards, narrowing, generics, `unknown`/`any` removal, exhaustiveness |
| Security | Auth, injection, secrets exposure, access control |
| Performance | N+1 queries, missed memoization, unnecessary re-renders, allocation in hot paths |
| Naming/clarity | Variable names, function names, confusing logic |
| Testing | Missing tests, weak assertions, test quality |
| Architecture | Coupling, responsibility boundaries, abstraction levels |

**If a cluster has 3+ comments AND at least one previously-resolved thread shares the category:** Fix the underlying pattern rather than addressing each comment individually. State the systemic fix and reference which comments it addresses.

**If unresolved comments alongside resolved ones span the same area:** the reviewer isn't satisfied with previous fixes. Prioritize those threads.

For fewer than 3 unresolved comments, skip clustering and resolve directly.

## Phase 3: Resolve (parallel)

Create a TodoWrite list grouped by severity:
- **Critical**: Logic bugs, security issues, broken functionality
- **Important**: Code quality, missing tests, architecture concerns
- **Minor**: Style, naming, convention fixes
- **Questions**: Clarifications to answer (not code changes)

Spawn a `ia-pr-comment-resolver` agent for each item in parallel. For systemic clusters, spawn one agent for the cluster with all related comments in its prompt.

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

The `unresolved` array should be empty. If threads remain there, repeat from Phase 1.

Run `ia-verification-before-completion` before reporting done.

## Scripts

- [scripts/get-pr-comments](scripts/get-pr-comments) - GraphQL query returning `{unresolved, cross_invocation: {signal, resolved_threads}}`
- [scripts/resolve-pr-thread](scripts/resolve-pr-thread) - GraphQL mutation to resolve a thread by ID

## Success Criteria

- All unresolved review threads addressed
- Systemic patterns identified and fixed at the root (not comment-by-comment)
- Changes committed and pushed
- Threads resolved via GraphQL
- Empty `unresolved` array from get-pr-comments on verify
