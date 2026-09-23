# Troubleshooting & Technical Details

## Troubleshooting

### "Worktree already exists"

The script offers to print its path. This does not transfer ownership or change the caller's working directory.

### "Cannot remove worktree: it is the current worktree"

Run cleanup with the main checkout as workdir. Obtain its path from `list`; `git rev-parse --show-toplevel` inside a linked checkout returns that linked checkout, not the main one.

```bash
env -C "$main_checkout" bash ${CLAUDE_PLUGIN_ROOT}/skills/ia-git-worktree/scripts/worktree-manager.sh cleanup feature-name
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

Use the main path shown by `list` for commands aimed at the main checkout:

```bash
env -C "$main_checkout" git status --short
```

### Cleanup refuses a tree

Supply explicit names and the `WORKTREE_SESSION_ID` set before creation. Do not reuse another session's token. Preserve any dirty, untracked, or ignored files, including copied environment files and dependencies; arrange their disposition under user authority before retrying. A locked tree remains protected by Git. A clean tree from this session can be removed after confirming no process uses it.

---

## Branch from a fresh remote base (manager-script behavior)

Do not run these steps manually; the script runs them. Read only when debugging why `create` branched from `origin/<base>` instead of a local branch, or why it fell back to a local ref.

When creating a worktree's branch from the default branch (`main`/`master`), the local base may be ahead of `origin/<base>` due to another session, worktree, or background task. Branching from local HEAD silently carries those unrelated commits into the new feature branch and the eventual PR. Checking out `<base>` in the caller's working tree to update it first is worse: it silently switches the user's active branch out from under them, which is why the script never does that.

The script's actual sequence (fetch-only, never checks out the caller's branch):

```bash
GIT_TERMINAL_PROMPT=0 git fetch --no-tags origin <base>
if [ $? -eq 0 ]; then
  base_ref="origin/<base>"
else
  base_ref="<base>"   # offline fallback: branch from the local ref
fi
git worktree add .worktrees/<name> -b <branch> "$base_ref"
```

A narrow `remote.origin.fetch` refspec makes `git fetch origin` silently partial. When the config maps only one branch, every other remote-tracking ref stays frozen, and `git log origin/<other>` or `git merge-base --is-ancestor` return stale answers with no error. Check `git config --get-all remote.origin.fetch`, and pass an explicit refspec before making any claim about another branch.

Known gap: the script does not distinguish "stale-base contamination" (another session advanced local `<base>` past `origin/<base>` with unrelated commits) from "forgot-to-branch" (the user's own unpushed commits on local `<base>` that were meant for a feature branch); it always prefers `origin/<base>` when the fetch succeeds. To carry unpushed local commits on `<base>` forward into the new branch instead, branch manually: `git worktree add <path> -b <branch> <base>`.

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
