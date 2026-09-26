---
name: ia-git-worktree
class: tool
description: >-
  Manage Git worktrees for isolated parallel development. Use when creating,
  listing, switching, or cleaning up git worktrees, or when needing isolated
  branches for concurrent reviews or feature work.
---

# Git worktree manager

**GATE: If the task runs inside an existing worktree (a worktree path is given and no create/remove/switch is requested), none of the creation flow applies: work in place and skip this skill.** To check: `git rev-parse --show-toplevel` appears as a linked entry in `git worktree list`.

## Working rules

- Preserve other sessions' branches, files, and staged work (see Ownership).
- Verify dependencies resolve first-party code from the intended worktree.
- Keep merge, push, and cleanup within user authorization; report the exact exercised checkout and resulting commit.

## Always use the manager script

Never call `git worktree add` directly; always use the `worktree-manager.sh` script.

The script handles critical setup that raw git commands don't:
1. Copies `.env`, `.env.local`, `.env.test`, etc. from main repo
2. Ensures `.worktrees` is in `.gitignore`
3. Creates consistent directory structure
4. After creation, install dependencies if detected: `package.json` → `npm install`, `composer.json` → `composer install`, `pyproject.toml` → `pip install -e .`, `go.mod` → `go mod download`

All commands use: `bash ${CLAUDE_PLUGIN_ROOT}/skills/ia-git-worktree/scripts/worktree-manager.sh <command>`. If `CLAUDE_PLUGIN_ROOT` is unset (non-Claude-Code harness), resolve the script relative to this skill's own directory.

Before creating worktrees, export a unique `WORKTREE_SESSION_ID` and retain that same value for this session's later manager calls. Example: `export WORKTREE_SESSION_ID="$(python3 -I -c 'import uuid; print(uuid.uuid4())')"`. The manager records ownership in each new worktree's Git metadata. Creation without a session ID works, but manager cleanup then refuses that tree; never adopt a previous session's ID to bypass ownership.

The manager script fetches `origin/<base>` fresh and branches from it; it never checks out `<base>` in the caller's working tree. If the fetch fails (offline, no remote), it falls back to the local `<base>` ref. PR review: pass the fetched PR head as `<base>`, then verify its SHA ([workflow-examples.md](./references/workflow-examples.md)). Details: [troubleshooting.md](./references/troubleshooting.md).


## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `create <branch> [from]` | Create worktree + branch (default: from main) | `...worktree-manager.sh create feature-login` |
| `list` / `ls` | List all worktrees with status | `...worktree-manager.sh list` |
| `switch <name>` / `go` | Print the registered worktree's absolute path; the caller applies it as workdir | `target=$(...worktree-manager.sh switch feature-login)` |
| `copy-env <name>` | Copy .env files to existing worktree | `...worktree-manager.sh copy-env feature-login` |
| `cleanup <name> [...]` / `clean` | Confirm removal of named, session-owned, clean worktrees | `...worktree-manager.sh cleanup feature-login` |

Run commands with `env -C "$target" <command>` or the harness workdir argument. A child script cannot change the caller's working directory. Listing and name resolution work from any main or linked checkout, including subdirectories.

Cleanup refuses the current checkout, another session's tree, and tracked, untracked, or ignored files. Auto-copied `.env` files and installed dependencies therefore require explicit user-managed disposition before cleanup. Confirm no process uses the named trees; the manager cannot detect every external reader. Git's normal removal safeguards remain enabled, including locked-tree refusal. Do not force deletion or suppress failures to finish cleanup.


## Safety Verification

Before creating a worktree, verify the worktree directory is gitignored:

```bash
# Verify .worktrees is ignored (should output ".worktrees")
git check-ignore .worktrees || echo "WARNING: .worktrees not in .gitignore"
```

If not ignored, add it to `.gitignore` before proceeding.

After creating a worktree, run the project's test suite (or its fastest relevant subset when the full suite is slow) to establish a clean baseline. Catch pre-existing failures in the worktree before starting new work, not mid-implementation.


## Ownership

- One writer per worktree. Treat every `git worktree list` entry not created **in the current session** as read-only; a tree left from a previous round is not the current session's either. Reuse is most tempting exactly where it is most dangerous: an existing tree already has dependencies and env wired up, and another session may be running a suite in it.
- Do not mutate a tree while the current session's suite runs there. Test runners load source files as they reach them, so a mid-run edit produces a mass-failure result that looks exactly like a real regression.
- A failure burst that contradicts a claim is a harness **hypothesis**, not a conclusion. Do not record or report the self-inflicted attribution until a re-run on a tree just asserted clean (`git status --short` empty) has returned.
- When a mutation is unavoidable, assert the restore (grep the token back to its original count, plus `git status --short`) rather than trusting `git checkout --`.
- One checkout has one index, so staging explicit paths does not scope a commit: `git add <mine> && git commit` also commits whatever a peer staged, under the current session's message. The protection is a pathspec on the commit itself (`git commit -- <paths>`), which takes those paths from the working tree and ignores the index; new files still need `git add`. It constrains that commit, not a peer's, so the residual control is latency between writing and committing. Read `git show --stat HEAD` afterwards and confirm only the intended files are there.
- `git -C <repo> push <remote> HEAD:<branch>` resolves `HEAD` in **that** repo, not in the worktree that was edited. Edits made in a linked worktree and pushed with `-C` at the main checkout publish the main checkout's commit onto the feature branch, and `--force-with-lease` does not catch it because the lease checks the branch's old value, not what `HEAD` names. Never spell `HEAD:` in a `-C` push; resolve the SHA in the worktree and push it explicitly, then confirm with `git ls-remote`. Two branches "updated" to one SHA, or a pushed subject unrelated to the work, is the tell.
- Linked worktrees share one stash stack. `git stash` writes to the common git directory, so a red/green cycle in one worktree can pop and drop a stash another worktree pushed in between. Never stash for red/green here: `git diff > /tmp/red.patch`, `git checkout -- <files>` (worktree-local) for the red run, `git apply /tmp/red.patch` for green. A dropped stash is still recoverable while its commit survives: `git stash store -m <message> <sha>` re-registers the SHA that `Dropped refs/stash@{0} (<sha>)` printed.
- A worktree's HEAD is shared mutable state, so answer branch questions from refs. Any other session can check something else out there, which makes `git -C <worktree> rev-parse HEAD` describe a different branch and report a correct push as a mismatch. Refs are shared across every worktree: ask any one of them about the branch by name (`rev-parse <branch>`, `rev-list --count origin/<branch>..<branch>`, `reflog <branch>`).

Use `env -C <worktree> <cmd>` for every command, never `cd`. A shell's cwd persists across calls, so one `cd <repo-root>` for an unrelated reason silently relocates every later command: probe files get written into the shared main tree and run against its bytes, and the tidy-up reflex `git checkout -- <path>` becomes a **write** aimed at the wrong tree. The `git -C` habit does not generalize: interpreters, test runners, linters, and a heredoc `cat >` all take the cwd. Have any probe print the tree it ran in.


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

## Task-specific references

Read the relevant reference before implementing or reviewing the matching behavior:

- For dependency provenance, environment adaptation, review/work workflows, branch completion, or hooks: [worktree-integration.md](./references/worktree-integration.md).

Existing specialized references, when the corresponding topic applies:
