---
name: ia-git-worktree
description: "Manage Git worktrees for isolated parallel development. Use when creating, listing, switching, or cleaning up git worktrees, or when needing isolated branches for concurrent reviews or feature work."
---

# Git worktree manager

**GATE: If the task runs inside an existing worktree (a worktree path is given and no create/remove/switch is requested), none of the creation flow applies: work in place and skip this skill.** To check: `git rev-parse --show-toplevel` appears as a linked entry in `git worktree list`.

## Working rules

- Preserve other sessions' branches, files, and staged work (see Ownership).
- Verify dependencies resolve first-party code from the intended worktree.
- Keep merge, push, and cleanup within user authorization; report the exact exercised checkout and resulting commit.

## Create worktrees with this procedure

Create every worktree with the steps below, not an ad hoc `git worktree add`. Record each tree this session creates; only those trees are this session's to clean up.

1. **Choose the path.** Use `.worktrees/<name>` under the main checkout. Confirm it is ignored: `git check-ignore -q -- .worktrees/<name>`. If it is not, append `.worktrees/` to `$(git rev-parse --git-path info/exclude)` (never the tracked `.gitignore`) and re-check. If a project rule still keeps it visible, stop and report the conflict. See [hooks-and-excludes.md](./references/hooks-and-excludes.md).
2. **Resolve the base to a commit without touching the caller's checkout.** Fetch into a private ref, pin its SHA, then remove the ref:

   ```bash
   fetch_ref="refs/whetstone/fetch/$(date +%s)-$$"
   if GIT_TERMINAL_PROMPT=0 git fetch --no-tags --refmap= origin "<base>:$fetch_ref"; then
     base_sha=$(git rev-parse --verify "$fetch_ref^{commit}")
   else
     base_sha=$(git rev-parse --verify "<base>^{commit}")
   fi
   git update-ref -d "$fetch_ref"
   ```

   Never check out `<base>` in the caller's working tree, and do not rely on `origin/<base>` or `FETCH_HEAD`, which other checkouts can move. To carry unpushed local commits on `<base>` into the branch, branch from the local ref deliberately and say so.
3. **Create the tree:** `git worktree add -b <branch> .worktrees/<name> "$base_sha"`, then verify `git -C .worktrees/<name> rev-parse HEAD` equals `$base_sha`. For an **untrusted base** (PR heads, fork or origin-only branches, third-party code), run `git -c core.hooksPath=/dev/null worktree add ...` so checkout hooks do not run.
4. **Environment files (trusted bases only).** Copy `.env`, `.env.local`, `.env.test`, and similar files from the main checkout only when the base is the default branch or a local branch that already contains the fetched commit. Never overwrite or follow an existing file or symlink in the new tree (`cp -n`, after checking with `test -L`). Never copy them into an untrusted tree.
5. **Dependencies.** For trusted bases, install what the project declares: `package.json` → `npm install`, `composer.json` → `composer install`, `pyproject.toml` → `pip install -e .`, `go.mod` → `go mod download`. For untrusted bases, skip installs where possible; if one is necessary, disable lifecycle scripts and plugins (`npm ci --ignore-scripts`, `composer install --no-scripts --no-plugins`), and do not run `pip install -e .`, which runs the build backend. Keep credentials out of commands run in that tree.

For a PR review, fetch the head into a review ref (`git fetch --no-tags origin "+pull/<n>/head:refs/review/pr-<n>"`), pass that ref as `<base>`, and treat the tree as the PR head only when both the review ref and the new branch equal `gh pr view <n> --json headRefOid -q .headRefOid`. On a mismatch, review `gh pr diff <n>` instead and say so in the coverage notes.

## Other operations

| Operation | Command |
|---------|---------|
| List | `git worktree list` |
| Path of a tree | `git worktree list --porcelain`, then the `worktree` line for the branch; the caller applies it as workdir |
| Clean up | For each named tree this session created: require `git -C <tree> status --porcelain --untracked-files=all --ignored=matching` to print nothing, confirm with the user, then `git worktree remove <tree>` from the main checkout |

Run commands with `env -C "$target" <command>` or the harness workdir argument. Run cleanup from the main checkout; inside a linked tree, `git rev-parse --show-toplevel` returns that linked tree.

Cleanup refuses the current checkout, another session's tree, and any tree with tracked, untracked, or ignored files. Copied `.env` files and installed dependencies therefore need explicit user-managed disposition first. Confirm no process uses the named trees. Keep Git's removal safeguards, including locked-tree refusal: never pass `--force` or suppress failures to finish cleanup. Before `git worktree prune` after a tree ran agent or third-party code, list `$(git rev-parse --git-common-dir)/worktrees` with `ls -la` and `unlink` any symlink there: prune follows planted symlinks and deletes their targets' contents.

A worktree under `.worktrees/` is a second checkout inside the repository. Tests that walk the tree with `rglob` or `find` see it even though Git excludes hide it; for parallel suites, create the worktrees outside the repository.


## Safety Verification

Before any baseline suite or migration, apply `ia-verification-before-completion`'s effective-target preflight. Resolve worktree environment/configuration overlays; verify disposable database and service targets, never the dev database. Copied `.env` files do not prove isolation. Without verified disposable targets, stop before tests. Then run the suite or its fastest relevant subset to establish a clean baseline before implementation.


## Ownership

- One writer per worktree. Treat every `git worktree list` entry not created **in the current session** as read-only; a tree left from a previous round is not the current session's either. Reuse is most tempting exactly where it is most dangerous: an existing tree already has dependencies and env wired up, and another session may be running a suite in it.
- Do not mutate a tree while the current session's suite runs there. Test runners load source files as they reach them, so a mid-run edit produces a mass-failure result that looks exactly like a real regression.
- A failure burst that contradicts a claim is a harness **hypothesis**, not a conclusion. Do not record or report the self-inflicted attribution until a re-run on a tree just asserted clean (`git status --short` empty) has returned.
- When a mutation is unavoidable, assert the restore (grep the token back to its original count, plus `git status --short`) rather than trusting `git checkout --`.
- One checkout has one index: a bare commit includes unrelated staged entries, while `git commit -- <paths>` records complete working-tree files, including caller or peer hunks. Use a pathspec commit only after establishing whole-file ownership of every selected change. For mixed hunks, commit the attributable patch in a clean session-owned checkout while preserving the caller's HEAD, index, and files. Inspect the exact proposed and committed patches, not only filenames or `--stat`; follow [commit-ownership.md](./references/commit-ownership.md).
- Never use `HEAD:` in a `git -C` push. Resolve the SHA in the edited worktree, push it explicitly, and confirm with `git ls-remote`; a lease cannot catch selection of another checkout's HEAD. Details: [commit-ownership.md](./references/commit-ownership.md).
- Never `git stash` for red/green: linked worktrees share one stash stack. Use the patch-file cycle and stash recovery in [commit-ownership.md](./references/commit-ownership.md).
- Answer branch questions from refs (`rev-parse <branch>`), not a worktree's HEAD, which other sessions can move; see [commit-ownership.md](./references/commit-ownership.md).

Use `env -C <worktree> <cmd>` for every command, never `cd`. A shell's cwd persists across calls, so one `cd <repo-root>` for an unrelated reason silently relocates every later command: probe files get written into the shared main tree and run against its bytes, and the tidy-up reflex `git checkout -- <path>` becomes a **write** aimed at the wrong tree. The `git -C` habit does not generalize: interpreters, test runners, linters, and a heredoc `cat >` all take the cwd. Have any probe print the tree it ran in.


## Verify

- `git worktree list` shows the new entry
- `.worktrees` is ignored, or inside the bare common directory
- Dependencies installed in the worktree (trusted bases; untrusted bases follow the rules above)
- Baseline test suite passes in the worktree


## References

- [hooks-and-excludes.md](./references/hooks-and-excludes.md) - Hook safety under Husky, .git/info/exclude vs .gitignore
- [commit-ownership.md](./references/commit-ownership.md) - Whole-file commits and isolated staging for mixed hunks

## Task-specific references

Read the relevant reference before implementing or reviewing the matching behavior:

- For dependency provenance, environment adaptation, review/work workflows, branch completion, or hooks: [worktree-integration.md](./references/worktree-integration.md).

Existing specialized references, when the corresponding topic applies:
