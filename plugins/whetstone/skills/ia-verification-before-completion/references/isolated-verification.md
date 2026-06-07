# Isolated Verification

A green build or test run in the working tree is not proof the change is sound. Unrelated work-in-progress already present -- uncommitted edits, untracked files, a sibling branch's leftovers -- can supply a missing symbol, satisfy an import, or mask a break that the change alone would expose. The contaminated local pass is not the evidence; a clean pass in isolation is.

When the change is high-stakes (touches shared modules consumed elsewhere) or the tree cannot be made clean first, reproduce the pass against a known-good commit with only the owned diff applied:

```bash
# 1. Stage a detached worktree at a known-good base (last green commit)
git worktree add --detach .worktrees/verify <known-good-commit>

# 2. Apply ONLY the diff of the files owned by this change
git diff -- path/to/owned-file path/to/other-owned-file | git apply --directory=.worktrees/verify -

# 3. Build and test there, in isolation
( cd .worktrees/verify && <build-command> && <test-command> )

# 4. Tear down
git worktree remove .worktrees/verify
```

A clean pass in the isolated tree is the proof. A failure there -- while the local tree stays green -- means surrounding WIP was masking the break: return to implementation, do not claim done. State which base commit and which files were isolated in the verification evidence.
