---
name: finishing-branch
description: >-
  Workflow closer for completed feature branches: commit, merge, PR, keep, or
  discard with safety checks. Use when finishing a branch, wrapping up work,
  creating a PR, merging a feature branch, or cleaning up after implementation.
---

# Finishing a Branch

## Prerequisites

Before running this skill, verify:

1. **All tests pass** — run the full test suite, not just new tests. If the project has no test suite, verify per `verification-before-completion` (diff review, syntax validation).
2. **All tasks complete** — check task list or plan file for unchecked items
3. **Verification evidence is fresh** — per `verification-before-completion`

If tests are failing, **stop here**. Show the failures and fix them first. If no test suite exists, state what you verified and how (see `verification-before-completion` — "When No Verification Command Exists").

## Guard: Must Be on a Feature Branch

Check the current branch before proceeding:

```bash
current_branch=$(git branch --show-current)
default_branch=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null)
default_branch=${default_branch##refs/remotes/origin/}
if [ -z "$default_branch" ]; then
  default_branch=$(git rev-parse --verify origin/main >/dev/null 2>&1 && echo "main" || echo "master")
fi
```

If `$current_branch` equals `$default_branch`, **stop** — ask the user if they intended to work directly on the default branch. Do not offer merge or discard options for the default branch.

**If no remote is configured** (`git remote` returns empty), only offer Option 1 (merge locally) and Option 3 (keep as-is). Disable Option 2 (push/PR) since there is no remote to push to.

## Stage and Commit

Before presenting options, ensure all work is committed:

1. Review changes: `git status` and `git diff`
2. Stage relevant files (prefer specific files over `git add .` to avoid staging secrets or large binaries)
3. Commit with conventional format:

```bash
git commit -m "feat(scope): description of what and why"
```

If incremental commits were already made during implementation (per `workflows:work` Phase 2), this step may be a no-op. Check `git status` — if clean, skip to options.

## Present Options

Present exactly four options using AskUserQuestion. Keep options concise — list the option names and when-to-use, don't add lengthy explanations. Let the user pick, then show the detailed steps.

### Option 1: Merge locally

**Steps:**
1. `git checkout $default_branch`
2. `git pull origin $default_branch`
3. `git merge --no-ff $feature_branch`
4. Run full test suite to verify merge is clean
5. If tests fail → abort merge, report failures, stay on feature branch
6. If tests pass → `git branch -d $feature_branch`

**When to use:** Solo work, small changes, no review needed.

### Option 2: Push and create PR

Push the branch to remote and open a pull request.

**Steps:**
1. `git push -u origin $feature_branch`
2. Create PR using `gh pr create` with the template below
3. Report the PR URL

**PR template:**
```
## Summary
- [What was built and why]
- [Key decisions made]

## Testing
- [Tests added/modified]
- [Manual testing performed]

## Post-Deploy Monitoring & Validation
- **What to monitor**: [logs, metrics, dashboards]
- **Expected healthy behavior**: [signals]
- **Failure signals / rollback trigger**: [trigger + action]
- **If no operational impact**: `No additional monitoring required: <reason>`

## Before / After Screenshots
| Before | After |
|--------|-------|
| ![before](URL) | ![after](URL) |
```

**When to use:** Team work, changes needing review, anything touching shared systems.

### Option 3: Keep as-is

Leave the branch where it is. No merge, no PR, no cleanup.

**Steps:**
1. Report: "Keeping branch `$feature_branch` at `$(pwd)`"
2. No cleanup performed

**When to use:** Work in progress, parking a branch for later, experimental changes.

### Option 4: Discard

Delete the branch and all changes. Destructive — requires confirmation.

**Steps:**
1. Warn about uncommitted changes and unpushed commits that will be permanently lost
2. Ask user to type "discard" to confirm
3. Only proceed if exact match
4. `git checkout $default_branch`
5. `git branch -D $feature_branch`
6. If branch exists on remote: `git push origin --delete $feature_branch`
7. If in a worktree, clean up the worktree

**When to use:** Abandoned experiments, wrong approach, starting over.

## Quick Reference

| Option | Commits? | Merges? | Pushes? | Keeps branch? | Cleans up? |
|--------|----------|---------|---------|---------------|------------|
| Merge locally | Yes | Yes | No | No (deleted) | Yes |
| Push + PR | Yes | No | Yes | Yes (remote) | No |
| Keep as-is | Yes | No | No | Yes (local) | No |
| Discard | No | No | No | No (deleted) | Yes |

## Worktree Cleanup

If working in a git worktree (not the main working tree):

- **After merge or discard:** clean up immediately:
  ```bash
  git worktree list                          # find the worktree path
  git worktree remove <worktree-path>        # remove it
  git branch -d <branch-name>               # delete the branch if merged
  ```
- **After PR:** keep the worktree until PR is merged, then clean up
- **Keep as-is:** worktree stays

## Safety Rules

- Never proceed with failing tests
- Never delete without typed "discard" confirmation
- Never force-push without explicit user request
- Never merge directly to main/master without explicit user permission
- Always run tests after merge to catch integration issues
- If tests fail after merge: revert the merge (`git revert -m 1 HEAD`), do not delete the branch, diagnose the integration failure

## Integration

This skill is the final step in the workflow chain:
- **Called by:** `workflows:work` (Phase 4)
- **Predecessor:** `verification-before-completion` (always run first)
- **Pairs with:** `git-worktree` for worktree lifecycle management

## Workflow Chain

```
brainstorming → workflows:plan → workflows:work → finishing-branch
                                                        ↓
                                              merge / PR / keep / discard
```
