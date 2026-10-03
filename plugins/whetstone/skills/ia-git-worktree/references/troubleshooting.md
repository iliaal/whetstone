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

### Tree-scanning tests fail with phantom offenders?

A worktree under `.worktrees/` is a full second checkout inside the repository. `.gitignore` hides it from Git, not from a test that walks the tree with `rglob` or `find`, so a hygiene test reports offenders that repeat known-good files under the worktree prefix, and CI never reproduces the failure. Check `git worktree list` before debugging one. Remove only this session's clean trees through the manager, or run the suite from a checkout that contains no nested worktree; for parallel suites, create the worktrees outside the repository.

---

## Branch from a fresh remote base (manager-script behavior)

Do not run these steps manually; the script runs them. Read only when debugging the resolved fetched commit or the local-ref fallback.

When creating a worktree's branch from the default branch (`main`/`master`), the local base may be ahead of `origin/<base>` due to another session, worktree, or background task. Branching from local HEAD silently carries those unrelated commits into the new feature branch and the eventual PR. Checking out `<base>` in the caller's working tree to update it first is worse: it silently switches the user's active branch out from under them, which is why the script never does that.

The script's actual sequence (fetch-only, never checks out the caller's branch):

```bash
fetch_marker=$(mktemp "${TMPDIR:-/tmp}/whetstone-fetch.XXXXXXXXXX")
fetch_ref="refs/whetstone/fetch/${fetch_marker##*/}"
GIT_TERMINAL_PROMPT=0 git fetch --no-tags --refmap= origin "<base>:$fetch_ref"
if [ $? -eq 0 ]; then
  base_sha=$(git rev-parse --verify "$fetch_ref^{commit}")
else
  base_sha=$(git rev-parse --verify '<base>^{commit}')
fi
git update-ref -d "$fetch_ref"
rm -- "$fetch_marker"
git worktree add .worktrees/<name> -b <branch> "$base_sha"
```

A narrow `remote.origin.fetch` refspec can leave remote-tracking refs frozen even after an explicit branch fetch succeeds. `FETCH_HEAD` is also shared between linked checkouts, so another fetch can overwrite it. The manager uses its own private destination, pins that SHA, removes its ref, and verifies the created checkout against the SHA. It does not assume `origin/<base>` was updated. For separate claims about remote-tracking history, check `git config --get-all remote.origin.fetch` and fetch an explicit destination refspec first.

Known gap: the script does not distinguish "stale-base contamination" (another session advanced local `<base>` past the remote base with unrelated commits) from "forgot-to-branch" (the user's own unpushed commits on local `<base>` that were meant for a feature branch); it always prefers the fetched remote commit when the fetch succeeds. To carry unpushed local commits on `<base>` forward into the new branch instead, branch manually: `git worktree add <path> -b <branch> <base>`.

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
