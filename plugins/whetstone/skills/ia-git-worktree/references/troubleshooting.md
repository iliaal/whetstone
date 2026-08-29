# Troubleshooting & Technical Details

## Troubleshooting

### "Worktree already exists"

If you see this, the script will ask if you want to switch to it instead.

### "Cannot remove worktree: it is the current worktree"

Switch out of the worktree first (to main repo), then cleanup:

```bash
cd $(git rev-parse --show-toplevel)
bash ${CLAUDE_PLUGIN_ROOT}/skills/ia-git-worktree/scripts/worktree-manager.sh cleanup
```

### Lost in a worktree?

See where you are:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/ia-git-worktree/scripts/worktree-manager.sh list
```

### .env files missing in worktree?

If a worktree was created without .env files (e.g., via raw `git worktree add`), copy them:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/ia-git-worktree/scripts/worktree-manager.sh copy-env feature-name
```

Navigate back to main:

```bash
cd $(git rev-parse --show-toplevel)
```

---

## Branch from a fresh remote base (manager-script behavior)

Do not run these steps manually; the script runs them. Read only when debugging why `create` branched from `origin/<base>` instead of a local branch, or why it fell back to a local ref.

When creating a worktree's branch from the default branch (`main`/`master`), the local base may be ahead of `origin/<base>` due to another session, worktree, or background task. Branching from local HEAD silently carries those unrelated commits into the new feature branch and the eventual PR. Checking out `<base>` in the caller's working tree to update it first is worse -- it silently switches the user's active branch out from under them, which is why the script never does that.

The script's actual sequence -- fetch-only, never checks out the caller's branch:

```bash
GIT_TERMINAL_PROMPT=0 git fetch --no-tags origin <base>
if [ $? -eq 0 ]; then
  base_ref="origin/<base>"
else
  base_ref="<base>"   # offline fallback: branch from the local ref
fi
git worktree add .worktrees/<name> -b <branch> "$base_ref"
```

Known gap: the script does not distinguish "stale-base contamination" (another session advanced local `<base>` past `origin/<base>` with unrelated commits) from "forgot-to-branch" (the user's own unpushed commits on local `<base>` that were meant for a feature branch) -- it always prefers `origin/<base>` when the fetch succeeds. To carry unpushed local commits on `<base>` forward into the new branch instead, branch manually: `git worktree add <path> -b <branch> <base>`.

---

## Technical Details

### Directory Structure

```
.worktrees/
├── feature-login/          # Worktree 1
│   ├── .git
│   ├── app/
│   └── ...
├── feature-notifications/  # Worktree 2
│   ├── .git
│   ├── app/
│   └── ...
└── ...

.gitignore (updated to include .worktrees)
```

### How It Works

- Uses `git worktree add` for isolated environments
- Each worktree has its own branch
- Changes in one worktree don't affect others
- Share git history with main repo
- Can push from any worktree

### Performance

- Worktrees are lightweight (just file system links)
- No repository duplication
- Shared git objects for efficiency
- Much faster than cloning or stashing/switching
