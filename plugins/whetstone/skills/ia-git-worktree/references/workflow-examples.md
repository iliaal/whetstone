# Workflow Examples

## Code Review with Worktree

```bash
# Claude Code recognizes you're not on the PR branch
# Offers: "Use worktree for isolated review? (y/n)"

# You respond: yes
export WORKTREE_SESSION_ID="$(python3 -c 'import uuid; print(uuid.uuid4())')"
# Script runs (copies .env files automatically):
bash ${CLAUDE_PLUGIN_ROOT}/skills/ia-git-worktree/scripts/worktree-manager.sh create pr-123-feature-name

# Apply the returned path to each review command's workdir:
target=$(bash ${CLAUDE_PLUGIN_ROOT}/skills/ia-git-worktree/scripts/worktree-manager.sh switch pr-123-feature-name)
env -C "$target" git status --short

# After integrating work and disposing of generated/ignored files with authorization:
bash ${CLAUDE_PLUGIN_ROOT}/skills/ia-git-worktree/scripts/worktree-manager.sh cleanup pr-123-feature-name
```

## Parallel Feature Development

```bash
# For first feature (copies .env files):
export WORKTREE_SESSION_ID="$(python3 -c 'import uuid; print(uuid.uuid4())')"
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
