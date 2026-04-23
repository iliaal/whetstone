# Workflow Examples

## Code Review with Worktree

```bash
# Claude Code recognizes you're not on the PR branch
# Offers: "Use worktree for isolated review? (y/n)"

# You respond: yes
# Script runs (copies .env files automatically):
bash ${CLAUDE_PLUGIN_ROOT}/skills/ia-git-worktree/scripts/worktree-manager.sh create pr-123-feature-name

# You're now in isolated worktree for review with all env vars
cd .worktrees/pr-123-feature-name

# After review, return to main:
cd ../..
bash ${CLAUDE_PLUGIN_ROOT}/skills/ia-git-worktree/scripts/worktree-manager.sh cleanup
```

## Parallel Feature Development

```bash
# For first feature (copies .env files):
bash ${CLAUDE_PLUGIN_ROOT}/skills/ia-git-worktree/scripts/worktree-manager.sh create feature-login

# Later, start second feature (also copies .env files):
bash ${CLAUDE_PLUGIN_ROOT}/skills/ia-git-worktree/scripts/worktree-manager.sh create feature-notifications

# List what you have:
bash ${CLAUDE_PLUGIN_ROOT}/skills/ia-git-worktree/scripts/worktree-manager.sh list

# Switch between them as needed:
bash ${CLAUDE_PLUGIN_ROOT}/skills/ia-git-worktree/scripts/worktree-manager.sh switch feature-login

# Return to main and cleanup when done:
cd .
bash ${CLAUDE_PLUGIN_ROOT}/skills/ia-git-worktree/scripts/worktree-manager.sh cleanup
```
