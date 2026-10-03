# Commit ownership

Read before committing when caller changes, peer changes, or an existing index may overlap the task.

1. Resolve any missing manager setup (`.worktrees` ignore entry) before the caller-state snapshot. Record the caller's HEAD, exact staged and unstaged patches, untracked paths, and index state before editing. Establish which complete changes belong to the task. Stop writers before taking the snapshot or committing.
2. For wholly owned files, inspect their complete proposed working-tree patch against HEAD. A pathspec commit (`git commit -- <paths>`) records those entire files; use it only when every included hunk is task-owned. New files require staging first. Verify the exact committed patch with `git show --format=fuller --binary --no-ext-diff --no-textconv <commit>` and confirm unrelated staged intent remains intact.
3. For mixed hunks or unclear whole-file ownership, create a clean session-owned checkout from the captured caller HEAD through the manager. Construct an owned patch against that baseline: exclude caller/peer hunks and include required additions, deletions, modes, and binary changes. Do not copy the complete dirty file or apply the caller's whole diff.
4. Apply only that patch in the isolated checkout. Inspect its exact staged patch, confirm every hunk is owned and the index contains no unrelated paths, run the applicable checks there, and commit normally in that checkout. Verify the exact committed patch against the captured baseline.
5. Retain the resulting commit SHA and branch for authorized integration. Confirm the caller's HEAD, original staged and unstaged patches, untracked files, and index are unchanged. Do not push the caller's branch as though it contains the isolated commit. Report the actual committed checkout and branch.

An alternate-index commit that advances the caller's HEAD while retaining the old normal index leaves staged reversals of the task's changes. Use the isolated-checkout path when caller state must remain intact; integrate only after arranging its preservation under the user's authority. If the attributable patch cannot be separated safely, finish independent work and report the ownership conflict.

## Publish the actual commit

`git -C <repo> push <remote> HEAD:<branch>` resolves HEAD in that checkout, not the worktree that was edited. Pushing from the main checkout can therefore overwrite the feature branch with the main checkout's commit. `--force-with-lease` checks the remote branch's old value, not which commit HEAD names. Resolve the SHA in the edited checkout, push it explicitly, and confirm the remote ref with `git ls-remote`. Two branches updated to one SHA or an unrelated pushed subject indicate a possible checkout mix-up.
