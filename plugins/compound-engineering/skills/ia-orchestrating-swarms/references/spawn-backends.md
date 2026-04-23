# Spawn Backends

A **backend** determines how teammate Claude instances actually run. Claude Code supports three backends, and **auto-detects** the best one based on your environment.

## Backend Comparison

| Backend | How It Works | Visibility | Persistence | Speed |
|---------|-------------|------------|-------------|-------|
| **in-process** | Same Node.js process as leader | Hidden (background) | Dies with leader | Fastest |
| **tmux** | Separate terminal in tmux session | Visible in tmux | Survives leader exit | Medium |
| **iterm2** | Split panes in iTerm2 window | Visible side-by-side | Dies with window | Medium |

## Auto-Detection Logic

Detection checks (in order):
1. `$TMUX` environment variable set -> inside tmux -> use **tmux** backend
2. `$TERM_PROGRAM === "iTerm.app"` or `$ITERM_SESSION_ID` set -> in iTerm2
   - `it2` CLI installed -> use **iterm2** backend
   - `it2` not installed, tmux available -> use **tmux** (prompt to install it2)
   - Neither -> error: install tmux or it2
3. `which tmux` succeeds -> tmux available -> use **tmux** (external session)
4. Nothing available -> use **in-process**

## in-process (Default for non-tmux)

Teammates run as async tasks within the same Node.js process.

```
+-------------------------------------+
|           Node.js Process           |
|  +---------+  +---------+  +-----+ |
|  | Leader  |  |Worker 1 |  |W 2  | |
|  | (main)  |  | (async) |  |(as) | |
|  +---------+  +---------+  +-----+ |
+-------------------------------------+
```

**Pros:** Fastest startup, lowest overhead, works everywhere.
**Cons:** Can't see teammate output, all die if leader dies, harder to debug.

```javascript
// in-process is automatic when not in tmux
Task({
  team_name: "my-project",
  name: "worker",
  subagent_type: "general-purpose",
  prompt: "...",
  run_in_background: true
})

// Force in-process explicitly
// export CLAUDE_CODE_SPAWN_BACKEND=in-process
```

## tmux

Teammates run as separate Claude instances in tmux panes/windows.

**Inside tmux (native):** Splits your current window.
**Outside tmux (external session):** Creates a new tmux session called `claude-swarm`. View with `tmux attach -t claude-swarm`.

**Pros:** See teammate output in real-time, teammates survive leader exit, works in CI/headless.
**Cons:** Slower startup, requires tmux installed, more resource usage.

```bash
# Start tmux session first
tmux new-session -s claude

# Or force tmux backend
export CLAUDE_CODE_SPAWN_BACKEND=tmux
```

**Useful tmux commands:**
```bash
tmux list-panes              # List all panes in current window
tmux select-pane -t 1        # Switch to pane by number
tmux kill-pane -t %5         # Kill a specific pane
tmux attach -t claude-swarm  # View swarm session (if external)
tmux select-layout tiled     # Rebalance pane layout
```

## iterm2 (macOS only)

Teammates run as split panes within your iTerm2 window using iTerm2's Python API via `it2` CLI.

**Pros:** Visual debugging, native macOS experience, automatic pane management.
**Cons:** macOS + iTerm2 only, requires setup, panes die with window.

**Setup:**
```bash
# 1. Install it2 CLI
uv tool install it2
# OR: pipx install it2
# OR: pip install --user it2

# 2. Enable Python API in iTerm2
# iTerm2 -> Settings -> General -> Magic -> Enable Python API

# 3. Restart iTerm2

# 4. Verify
it2 --version
it2 session list
```

If setup fails, Claude Code will prompt you to set up it2 when you first spawn a teammate. You can choose to install it2 now, use tmux instead, or cancel.

## Forcing a Backend

```bash
# Force in-process (fastest, no visibility)
export CLAUDE_CODE_SPAWN_BACKEND=in-process

# Force tmux (visible panes, persistent)
export CLAUDE_CODE_SPAWN_BACKEND=tmux

# Auto-detect (default)
unset CLAUDE_CODE_SPAWN_BACKEND
```

## Backend in Team Config

The backend type is recorded per-teammate in `config.json`:

```json
{
  "members": [
    {
      "name": "worker-1",
      "backendType": "in-process",
      "tmuxPaneId": "in-process"
    },
    {
      "name": "worker-2",
      "backendType": "tmux",
      "tmuxPaneId": "%5"
    }
  ]
}
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| "No pane backend available" | Neither tmux nor iTerm2 available | Install tmux: `brew install tmux` |
| "it2 CLI not installed" | In iTerm2 but missing it2 | Run `uv tool install it2` |
| "Python API not enabled" | it2 can't communicate with iTerm2 | Enable in iTerm2 Settings -> General -> Magic |
| Workers not visible | Using in-process backend | Start inside tmux or iTerm2 |
| Workers dying unexpectedly | Outside tmux, leader exited | Use tmux for persistence |

## Checking Current Backend

```bash
# See what backend was detected
cat ~/.claude/teams/{team}/config.json | jq '.members[].backendType'

# Check if inside tmux
echo $TMUX

# Check if in iTerm2
echo $TERM_PROGRAM

# Check tmux availability
which tmux

# Check it2 availability
which it2
```
