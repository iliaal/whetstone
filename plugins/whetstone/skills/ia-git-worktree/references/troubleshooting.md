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

Do not run these steps manually; the script runs them. Read only when debugging why `create` prompted about unpushed commits.

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
