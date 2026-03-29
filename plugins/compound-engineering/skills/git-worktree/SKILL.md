---
name: git-worktree
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

After creating a worktree, run the project's test suite to establish a clean baseline. Pre-existing failures in the worktree should be caught before starting new work -- not discovered mid-implementation.

```bash
# CORRECT - Always use the script
bash ${CLAUDE_PLUGIN_ROOT}/skills/git-worktree/scripts/worktree-manager.sh create feature-name

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

All commands use: `bash ${CLAUDE_PLUGIN_ROOT}/skills/git-worktree/scripts/worktree-manager.sh <command>`

## Environment Detection

Before creating worktrees, detect the execution context:

1. **Already in a worktree?** Check `git rev-parse --show-toplevel` against `git worktree list`. If the current directory is already a linked worktree, skip creation -- work directly in the existing worktree.
2. **Codex/sandbox environment?** If `$CODEX_SANDBOX` is set or the repo is at a non-standard path (e.g., `/tmp/`, `/workspace/`), worktrees may not be supported. Fall back to regular branch switching.
3. **Bare repo?** If `git rev-parse --is-bare-repository` returns true, worktrees are the only way to have a working directory. Adjust paths accordingly.

Adapt the workflow to the detected context rather than failing with a generic error.

## Integration with Workflows

### `/workflows:review`

1. Check current branch
2. If ALREADY on target branch -> stay there, no worktree needed
3. If DIFFERENT branch -> offer worktree: "Use worktree for isolated review? (y/n)"

### `/workflows:work`

Always offer choice:
1. New branch on current worktree (live work)
2. Worktree (parallel work)

## Verify

- `git worktree list` shows the new entry
- `.worktrees` directory confirmed in `.gitignore`
- Dependencies installed in the worktree
- Baseline test suite passes in the worktree

## References

- [workflow-examples.md](./references/workflow-examples.md) - Code review and parallel development workflows
- [troubleshooting.md](./references/troubleshooting.md) - Common issues, directory structure, how it works
- [worktree-manager.sh](./scripts/worktree-manager.sh) - The manager script
