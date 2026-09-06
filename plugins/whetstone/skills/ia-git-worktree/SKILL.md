---
name: ia-git-worktree
class: tool
description: >-
  Manage Git worktrees for isolated parallel development. Use when creating,
  listing, switching, or cleaning up git worktrees, or when needing isolated
  branches for concurrent reviews or feature work.
---

# Git worktree manager

**GATE: If the task runs inside an existing worktree (a worktree path is given and no create/remove/switch is requested), none of the creation flow applies — work in place and skip this skill.** To check: `git rev-parse --show-toplevel` appears as a linked entry in `git worktree list`.

## Always use the manager script

Never call `git worktree add` directly -- always use the `worktree-manager.sh` script.

The script handles critical setup that raw git commands don't:
1. Copies `.env`, `.env.local`, `.env.test`, etc. from main repo
2. Ensures `.worktrees` is in `.gitignore`
3. Creates consistent directory structure
4. After creation, install dependencies if detected: `package.json` → `npm install`, `composer.json` → `composer install`, `pyproject.toml` → `pip install -e .`, `go.mod` → `go mod download`

All commands use: `bash ${CLAUDE_PLUGIN_ROOT}/skills/ia-git-worktree/scripts/worktree-manager.sh <command>`. If `CLAUDE_PLUGIN_ROOT` is unset (non-Claude-Code harness), resolve the script relative to this skill's own directory.

The manager script fetches `origin/<base>` fresh and branches from it -- it never checks out `<base>` in the caller's working tree. If the fetch fails (offline, no remote), it falls back to the local `<base>` ref. Details: [troubleshooting.md](./references/troubleshooting.md).

## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `create <branch> [from]` | Create worktree + branch (default: from main) | `...worktree-manager.sh create feature-login` |
| `list` / `ls` | List all worktrees with status | `...worktree-manager.sh list` |
| `switch <name>` / `go` | Switch to existing worktree | `...worktree-manager.sh switch feature-login` |
| `copy-env <name>` | Copy .env files to existing worktree | `...worktree-manager.sh copy-env feature-login` |
| `cleanup` / `clean` | Interactively remove inactive worktrees | `...worktree-manager.sh cleanup` |

After cleanup, run `git worktree prune` to remove any orphaned worktree metadata from manually deleted directories.

## Safety Verification

Before creating a worktree, verify the worktree directory is gitignored:

```bash
# Verify .worktrees is ignored (should output ".worktrees")
git check-ignore .worktrees || echo "WARNING: .worktrees not in .gitignore"
```

If not ignored, add it to `.gitignore` before proceeding.

After creating a worktree, run the project's test suite (or the fastest relevant subset if the full suite exceeds a few minutes) to establish a clean baseline. Pre-existing failures in the worktree should be caught before starting new work -- not discovered mid-implementation.

## Dependency Provenance

Never satisfy a worktree's gitignored dependency directory with a symlink to another checkout's. Generated autoloaders and module resolvers compute the application base directory from the *real* location of their own files, so the link resolves back into the donor tree and every first-party class or module loads from there -- your worktree's edits never execute, new files appear as "not found", and config comes from the other tree's `.env`. Give the worktree a real directory: `cp -al <donor>/vendor "$WT/vendor"` (hard links: same inodes, near-zero disk, correct base dir) for a read-only harness, or a full dereferencing copy / real install whenever anything will write into it -- hard links mean a package-manager write edits the donor too. Assert it once rather than assuming: print the resolved file path of one first-party symbol and confirm it names the worktree.

## Ownership

- One writer per worktree. Treat every `git worktree list` entry you did not create **in this session** as read-only -- a tree left from a previous round is not yours either. Reuse is most tempting exactly where it is most dangerous: an existing tree already has dependencies and env wired up, and another session may be running a suite in it.
- Do not mutate a tree while your own suite runs there. Test runners load source files as they reach them, so a mid-run edit produces a mass-failure result that looks exactly like a real regression.
- A failure burst that contradicts a claim is a harness **hypothesis**, not a conclusion. Do not record or report the self-inflicted attribution until a re-run on a tree you have just asserted clean (`git status --short` empty) has returned.
- When a mutation is unavoidable, assert the restore (grep the token back to its original count, plus `git status --short`) rather than trusting `git checkout --`.

Use `env -C <worktree> <cmd>` for every command, never `cd`. A shell's cwd persists across calls, so one `cd <repo-root>` for an unrelated reason silently relocates every later command: probe files get written into the shared main tree and run against its bytes, and the tidy-up reflex `git checkout -- <path>` becomes a **write** aimed at the wrong tree. The `git -C` habit does not generalize -- interpreters, test runners, linters, and a heredoc `cat >` all take the cwd. Have any probe print the tree it ran in.

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

Before writing any git hook, check `git config core.hooksPath` — Husky repos ignore `.git/hooks/` entirely. Personal tooling excludes go in `$(git rev-parse --git-path info/exclude)`, never the tracked `.gitignore`. Details: [hooks-and-excludes.md](./references/hooks-and-excludes.md)

## Verify

- `git worktree list` shows the new entry
- `.worktrees` directory confirmed in `.gitignore`
- Dependencies installed in the worktree
- Baseline test suite passes in the worktree

## References

- [workflow-examples.md](./references/workflow-examples.md) - Code review and parallel development workflows
- [troubleshooting.md](./references/troubleshooting.md) - Common issues, fresh-remote-base behavior, directory structure, how it works
- [hooks-and-excludes.md](./references/hooks-and-excludes.md) - Hook safety under Husky, .git/info/exclude vs .gitignore
- [worktree-manager.sh](./scripts/worktree-manager.sh) - The manager script
