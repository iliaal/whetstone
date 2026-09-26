# Workflow Examples

## Code Review with Worktree

```bash
# Claude Code recognizes you're not on the PR branch
# Offers: "Use worktree for isolated review? (y/n)"

# You respond: yes
export WORKTREE_SESSION_ID="$(python3 -I -c 'import uuid; print(uuid.uuid4())')"
# Fetch the PR head into a review ref; the caller's checkout and branches stay untouched.
# On GitHub, pull/<n>/head also resolves fork PRs. A same-named branch on origin may be unrelated.
git fetch --no-tags origin "+pull/123/head:refs/review/pr-123"
# Pass the review ref as the base. Without it the manager branches from origin/main.
# Its own `git fetch origin refs/review/pr-123` fails (no such remote ref) and it
# falls back to the local ref, which is the intended base. Copies .env files automatically:
bash ${CLAUDE_PLUGIN_ROOT}/skills/ia-git-worktree/scripts/worktree-manager.sh create pr-123-feature-name refs/review/pr-123

# Apply the returned path to each review command's workdir:
target=$(bash ${CLAUDE_PLUGIN_ROOT}/skills/ia-git-worktree/scripts/worktree-manager.sh switch pr-123-feature-name)
env -C "$target" git status --short

# A successful fetch is not proof. Treat the worktree as the PR head only when the review
# ref and the worktree's branch both equal headRefOid; ask refs, not the worktree HEAD
# (shared mutable state). On a mismatch (wrong ref, or the PR gained commits), stop,
# review `gh pr diff 123` hunks instead, and say so in the review's coverage notes:
pr_head=$(gh pr view 123 --json headRefOid -q .headRefOid)
[ "$(git rev-parse refs/review/pr-123)" = "$pr_head" ] \
  && [ "$(git rev-parse pr-123-feature-name)" = "$pr_head" ] \
  || { echo "review ref is not the PR head; review gh pr diff 123 instead" >&2; exit 1; }

# After integrating work and disposing of generated/ignored files with authorization:
bash ${CLAUDE_PLUGIN_ROOT}/skills/ia-git-worktree/scripts/worktree-manager.sh cleanup pr-123-feature-name
```

## Parallel Feature Development

```bash
# For first feature (copies .env files):
export WORKTREE_SESSION_ID="$(python3 -I -c 'import uuid; print(uuid.uuid4())')"
bash ${CLAUDE_PLUGIN_ROOT}/skills/ia-git-worktree/scripts/worktree-manager.sh create feature-login

# Later, start second feature (also copies .env files):
bash ${CLAUDE_PLUGIN_ROOT}/skills/ia-git-worktree/scripts/worktree-manager.sh create feature-notifications

# List what you have:
bash ${CLAUDE_PLUGIN_ROOT}/skills/ia-git-worktree/scripts/worktree-manager.sh list

# Switch between them as needed:
target=$(bash ${CLAUDE_PLUGIN_ROOT}/skills/ia-git-worktree/scripts/worktree-manager.sh switch feature-login)
env -C "$target" git status --short

# With both trees clean, integrated, and no processes using them:
bash ${CLAUDE_PLUGIN_ROOT}/skills/ia-git-worktree/scripts/worktree-manager.sh cleanup feature-login feature-notifications
```
