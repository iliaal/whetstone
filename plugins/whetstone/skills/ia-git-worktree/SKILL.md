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

The manager script branches from a fresh `origin/<base>`; if the prompt is unanswered it defaults to `origin/<base>` and lists unpushed commits in its output — report them in the change summary. Details: [troubleshooting.md](./references/troubleshooting.md).

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

When work in a worktree is done, verify tests pass, then present exactly 4 options. Ask via AskUserQuestion (Claude Code; load with ToolSearch `select:AskUserQuestion` if not loaded) or request_user_input (Codex); fall back to numbered options in chat.

1. **Merge locally** -- merge into base branch, delete worktree branch, clean up worktree
2. **Push + PR** -- push branch, create PR with `gh pr create`, keep worktree until merged
3. **Keep as-is** -- leave branch and worktree for later
4. **Discard** -- requires typing "discard" to confirm. Deletes branch and worktree. No silent discards.

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
