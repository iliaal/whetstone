# Worktree integration

## Dependency Provenance

Never satisfy a worktree's gitignored dependency directory with a symlink to another checkout's. Generated autoloaders and module resolvers compute the application base directory from the *real* location of their own files, so the link resolves back into the donor tree and every first-party class or module loads from there -- your worktree's edits never execute, new files appear as "not found", and config comes from the other tree's `.env`. Give the worktree a real directory: `cp -al <donor>/vendor "$WT/vendor"` (hard links: same inodes, near-zero disk, correct base dir) for a read-only harness, or a full dereferencing copy / real install whenever anything will write into it -- hard links mean a package-manager write edits the donor too. Assert it once rather than assuming: print the resolved file path of one first-party symbol and confirm it names the worktree.


## Environment Detection

Before creating worktrees, detect the execution context:

1. **Codex/sandbox environment?** If `$CODEX_SANDBOX` is set or the repo is at a non-standard path (e.g., `/tmp/`, `/workspace/`), worktrees may not be supported. Fall back to regular branch switching.
2. **Bare repo?** If `git rev-parse --is-bare-repository` returns true, worktrees are the only way to have a working directory. Adjust paths accordingly.

Adapt the workflow to the detected context rather than failing with a generic error.


## Integration with Workflows

### Code review (`/ia-review` in Claude Code)

1. Check current branch
2. If ALREADY on target branch -> stay there, no worktree needed
3. If DIFFERENT branch -> Ask via AskUserQuestion (Claude Code; load with ToolSearch `select:AskUserQuestion` if not loaded) or request_user_input (Codex); fall back to numbered options in chat. Options: 1) review in a new worktree 2) switch branch in place

### Plan execution (`/ia-work` in Claude Code)

Always offer choice:
1. New branch on current worktree (live work)
2. Worktree (parallel work)


## Branch Completion

When work in a worktree is done, verify tests pass, then present exactly 3 options. Ask via AskUserQuestion (Claude Code; load with ToolSearch `select:AskUserQuestion` if not loaded) or request_user_input (Codex); fall back to numbered options in chat.

1. **Merge locally** -- merge into base branch, delete worktree branch, clean up worktree
2. **Push + PR** -- push branch, create PR with `gh pr create`, keep worktree until merged
3. **Keep as-is** -- leave branch and worktree for later
Discarding is never offered as an option. Delete the branch and worktree only when the user asks for it explicitly, and require typing "discard" to confirm first. No silent discards.


## Change Summary

When completing work in a worktree (before merge or PR), output a structured summary:

```
CHANGES MADE:
- src/routes/tasks.ts: Added validation middleware

THINGS I DIDN'T TOUCH (intentionally):
- src/routes/auth.ts: Has similar validation gap but out of scope

POTENTIAL CONCERNS:
- The Zod schema is strict -- rejects extra fields. Confirm this is desired.
```

The "DIDN'T TOUCH" section prevents reviewers from wondering whether adjacent issues were missed or intentionally deferred.


## Hooks and Local Excludes

Before writing any git hook, check `git config core.hooksPath` — Husky repos ignore `.git/hooks/` entirely. Personal tooling excludes go in `$(git rev-parse --git-path info/exclude)`, never the tracked `.gitignore`. Details: [hooks-and-excludes.md](./hooks-and-excludes.md)

In a linked worktree `.git` is a file, so every `.git/<state-file>` test is wrong: `test -f .git/MERGE_HEAD` reports "no merge in progress" in the middle of a conflict, because per-worktree state lives in the common dir under `worktrees/<name>/`. Ask the plumbing instead -- `git rev-parse -q --verify MERGE_HEAD` for the state, `git rev-parse --git-path <file>` for the path. Same for `REBASE_HEAD`, `CHERRY_PICK_HEAD`, and hook paths.
