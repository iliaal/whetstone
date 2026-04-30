---
name: ia-git-worktree
class: tool
description: >-
  Manage Git worktrees for isolated parallel development. Use when creating,
  listing, switching, or cleaning up git worktrees, or when needing isolated
  branches for concurrent reviews or feature work.
---

# Git worktree manager

## Always use the manager script

Never call `git worktree add` directly -- always use the `worktree-manager.sh` script.

The script handles critical setup that raw git commands don't:
1. Copies `.env`, `.env.local`, `.env.test`, etc. from main repo
2. Ensures `.worktrees` is in `.gitignore`
3. Creates consistent directory structure
4. After creation, install dependencies if detected: `package.json` → `npm install`, `composer.json` → `composer install`, `pyproject.toml` → `pip install -e .`, `go.mod` → `go mod download`

## Safety Verification

Before creating a worktree, verify the worktree directory is gitignored:

```bash
# Verify .worktrees is ignored (should output ".worktrees")
git check-ignore .worktrees || echo "WARNING: .worktrees not in .gitignore"
```

If not ignored, add it to `.gitignore` before proceeding. The manager script handles this, but verify when troubleshooting.

### Branch from a fresh remote base (manager-script behavior)

This subsection documents the safety logic `worktree-manager.sh create` implements when branching from the default branch — it is not a manual sequence to run. The script handles the steps; the rationale lives here so users can reason about the behavior.

When creating a worktree's branch from the default branch (`main`/`master`), the local base may be ahead of `origin/<base>` due to another session, worktree, or background task. Branching from local HEAD silently carries those unrelated commits into the new feature branch and the eventual PR — and an unconditional `git reset --hard origin/<base>` would silently drop the user's intentional unpushed work.

The script's safe sequence:

```bash
git fetch --no-tags origin <base>
unpushed=$(git log "origin/$base..$base" --oneline)
if [ -n "$unpushed" ]; then
  # Surface the commit list and prompt: carry forward (base_ref=$base) or leave on local <base> (base_ref=origin/$base)
  ...
fi
git worktree add .worktrees/<name> -b <branch> "$base_ref"
```

Two failure modes the prompt distinguishes:

- **Stale-base contamination** — another session advanced local `<base>` past `origin/<base>` with unrelated commits. The user wants `origin/<base>` as the new branch's base; the unpushed commits stay on local `<base>` for separate handling.
- **Forgot-to-branch** — the user authored real commits on local `<base>` intending them for a feature branch. The user wants HEAD as the new branch's base so the commits carry forward.

Local git state alone cannot distinguish these (author email is unreliable in multi-session setups), so the script surfaces the choice rather than guessing. Default fallback when the user can't be reached: branch from `origin/<base>` and report the unpushed commits in the change summary so the user resolves them deliberately. If the script does not implement this yet, that is a known gap — open an issue rather than working around with raw `git worktree add`.

After creating a worktree, run the project's test suite to establish a clean baseline. Pre-existing failures in the worktree should be caught before starting new work -- not discovered mid-implementation.

```bash
# CORRECT - Always use the script
bash ${CLAUDE_PLUGIN_ROOT}/skills/ia-git-worktree/scripts/worktree-manager.sh create feature-name

# WRONG - Never do this directly
git worktree add .worktrees/feature-name -b feature-name main
```

## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `create <branch> [from]` | Create worktree + branch (default: from main) | `...worktree-manager.sh create feature-login` |
| `list` / `ls` | List all worktrees with status | `...worktree-manager.sh list` |
| `switch <name>` / `go` | Switch to existing worktree | `...worktree-manager.sh switch feature-login` |
| `copy-env <name>` | Copy .env files to existing worktree | `...worktree-manager.sh copy-env feature-login` |
| `cleanup` / `clean` | Interactively remove inactive worktrees | `...worktree-manager.sh cleanup` |

After cleanup, run `git worktree prune` to remove any orphaned worktree metadata from manually deleted directories.

All commands use: `bash ${CLAUDE_PLUGIN_ROOT}/skills/ia-git-worktree/scripts/worktree-manager.sh <command>`

## Environment Detection

Before creating worktrees, detect the execution context:

1. **Already in a worktree?** Check `git rev-parse --show-toplevel` against `git worktree list`. If the current directory is already a linked worktree, skip creation -- work directly in the existing worktree.
2. **Codex/sandbox environment?** If `$CODEX_SANDBOX` is set or the repo is at a non-standard path (e.g., `/tmp/`, `/workspace/`), worktrees may not be supported. Fall back to regular branch switching.
3. **Bare repo?** If `git rev-parse --is-bare-repository` returns true, worktrees are the only way to have a working directory. Adjust paths accordingly.

Adapt the workflow to the detected context rather than failing with a generic error.

## Integration with Workflows

### `/ia-review`

1. Check current branch
2. If ALREADY on target branch -> stay there, no worktree needed
3. If DIFFERENT branch -> offer worktree: "Use worktree for isolated review? (y/n)"

### `/ia-work`

Always offer choice:
1. New branch on current worktree (live work)
2. Worktree (parallel work)

## Branch Completion

When work in a worktree is done, verify tests pass, then present exactly 4 options:

1. **Merge locally** -- merge into base branch, delete worktree branch, clean up worktree
2. **Push + PR** -- push branch, create PR with `gh pr create`, keep worktree until merged
3. **Keep as-is** -- leave branch and worktree for later
4. **Discard** -- requires typing "discard" to confirm. Deletes branch and worktree. No silent discards.

Clean up the worktree directory only for options 1 and 4. For option 2, the worktree stays until the PR merges.

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

## Hook Safety Under Husky

Installing hooks into `.git/hooks/` silently fails on any repo that uses Husky. Husky sets `core.hooksPath` (typically to `.husky/_`) and git ignores `.git/hooks/` entirely when that config is non-empty. The hook file lands on disk, is executable, is correct, and is dead. Invisible failure until someone asks why the post-merge behavior isn't running.

### Detection rule before writing any hook

```bash
hooks_path=$(git -C "$repo" config --get core.hooksPath)
```

- Empty output: write to `$(git rev-parse --git-common-dir)/hooks/<name>` as usual.
- `.husky/_` (or any path containing `husky.sh` / `h` trampoline): Husky v9 setup. Write to `.husky/<name>`; do NOT include the v8-era `. "$(dirname "$0")/_/husky.sh"` line (v9 prints a deprecation warning if you do).
- Unrecognized non-empty value: refuse to write the hook and surface the path to the user. Silent writes to the wrong location waste debug cycles later.

### Worktree-safe hook body

`.git/hooks/` lives in the common git dir and runs for every worktree of the clone. A hook installed once fires across all trees. Two rules to stay safe:

1. Resolve the invoking worktree's root inside the hook body with `git rev-parse --show-toplevel`, not a hardcoded path. Hardcoding means the last `install-hooks` invocation wins for every worktree.
2. Guard the tool invocation with an existence check on the tool's per-tree state dir. Siblings without your tool's setup must no-op, not spawn a failing background process per git op.

```sh
#!/bin/sh
root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -d "$root/.my-tool" ] || exit 0
( cd "$root" && my-tool index ) >>"$root/.my-tool/hook.log" 2>&1 &
exit 0
```

Redirect to a log file inside the tool's state dir, not `/dev/null` — silent failures produce stale state you only notice hours later.

## Local Excludes: .git/info/exclude vs .gitignore

Tooling artifacts (local index dirs, hook helpers, per-developer scratch files) belong in `.git/info/exclude`, NOT in the tracked `.gitignore`.

- `.gitignore` is content — tracked, shared with the team, reviewed in PRs. Adding a personal tooling rule there pollutes a shared file. On foreign repos (upstream projects, third-party clones) the rule either rides into a PR by accident or sits as a dirty working tree forever.
- `.git/info/exclude` is local — untracked, lives in the common git dir, shared across every worktree of the clone. Same syntax and semantics as `.gitignore` without the leakage.

### Resolving the path correctly under worktrees

Don't hardcode `$repo/.git/info/exclude`. In a worktree, `.git` is a file (gitlink), not a directory. Use git itself:

```bash
exclude=$(git -C "$repo" rev-parse --git-path info/exclude)
```

### Idempotent append

```bash
line="/.my-tool/"
mkdir -p "$(dirname "$exclude")"
grep -qxF "$line" "$exclude" 2>/dev/null || printf '\n# my-tool\n%s\n' "$line" >> "$exclude"
```

`grep -qxF` matches the exact line with no regex surprises.

### When to break the rule

Only when the artifact is genuinely team-shared and belongs in the repo (build outputs used in CI, generated files, vendored dependencies). If in doubt, ask: "would another contributor benefit from this rule?" If no, exclude locally.

## Verify

- `git worktree list` shows the new entry
- `.worktrees` directory confirmed in `.gitignore`
- Dependencies installed in the worktree
- Baseline test suite passes in the worktree

## References

- [workflow-examples.md](./references/workflow-examples.md) - Code review and parallel development workflows
- [troubleshooting.md](./references/troubleshooting.md) - Common issues, directory structure, how it works
- [worktree-manager.sh](./scripts/worktree-manager.sh) - The manager script
