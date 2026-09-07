# Spawn Backends

> When to read: when picking or debugging the spawn backend (Claude Agent teammates / subagents / subprocess), checking compatibility, or reasoning about where teammates actually execute.

A **backend** determines how teammate Claude instances actually run. Choose the supported `teammateMode` setting after checking the installed Claude Code version. Current versions default to `in-process`; `auto` enables environment-dependent pane selection.

## Backend Comparison

| Backend | How It Works | Visibility | Persistence | Speed |
|---------|-------------|------------|-------------|-------|
| **in-process** | Runs within the lead session | Agent panel and transcript | Session-bound | Low startup overhead |
| **tmux** | Separate terminal in tmux session | Visible in tmux | Confirm lifecycle; orphan panes are possible | Higher startup overhead |
| **iterm2** | Split panes in iTerm2 window | Visible side-by-side | Dies with window | Medium |

## Auto-Detection Logic

With `teammateMode: "auto"`, Claude selects a supported pane backend when the environment supports it and otherwise uses in-process mode. Check [official display-mode documentation](https://code.claude.com/docs/en/agent-teams#choose-a-display-mode) for the installed version's requirements; do not infer the mode from the presence of tmux alone.

## in-process (current default)

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
**Cons:** Session-bound lifecycle; use the agent panel to inspect teammate output.

```javascript
// With the in-process teammate mode selected
Agent({
  name: "worker",
  description: "Complete assigned work",
  subagent_type: "general-purpose",
  prompt: "...",
  run_in_background: true
})

// Select the mode in settings or use the supported teammate-mode CLI flag.
```

## tmux

Teammates run as separate Claude instances in tmux panes/windows.

**Inside tmux (native):** Splits your current window.
**Outside tmux:** Inspect the actual session/pane identifiers returned by the runtime; do not assume a fixed session name.

**Pros:** See teammate output in real time and inspect separate panes. Teammate spawning still requires an interactive Claude session; terminal visibility does not establish worker persistence.
**Cons:** Slower startup, requires tmux installed, more resource usage.

```bash
# Start tmux session first
tmux new-session -s claude

# Or force tmux backend
claude --teammate-mode tmux
```

**Useful tmux commands:**
```bash
tmux list-panes              # List all panes in current window
tmux select-pane -t 1        # Switch to pane by number
tmux kill-pane -t %5         # Kill a specific pane
tmux attach -t <session-name> # Use the observed owned session name
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

Set `teammateMode` in Claude settings, or choose it for an interactive session:

```bash
claude --teammate-mode in-process
claude --teammate-mode tmux
claude --teammate-mode auto
```

The flag is experimental; verify its supported values for the installed version. Do not rely on undocumented spawn-backend environment variables.

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
| Workers not visible | In-process panel or hidden idle row | Inspect the agent panel and transcript; select pane mode if needed |
| Workers dying unexpectedly | Session or worker failure | Inspect lifecycle evidence and owned edits before recovery |

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
