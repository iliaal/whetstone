# agent-browser CLI Reference

**ALWAYS use these Bash commands. NEVER use mcp__claude-in-chrome__* tools.**

Generate and record an invocation-owned session ID before running these examples. Substitute it for `[session-id]` in each call.

```bash
# Navigation
agent-browser --session "[session-id]" open "[url]"   # Navigate to URL
agent-browser --session "[session-id]" back           # Go back
agent-browser --session "[session-id]" close          # Close browser

# Snapshots (get element refs)
agent-browser --session "[session-id]" snapshot -i          # Interactive elements with refs (@e1, @e2, etc.)
agent-browser --session "[session-id]" snapshot -i --json   # JSON output

# Interactions (use refs from snapshot)
agent-browser --session "[session-id]" click @e1            # Click element
agent-browser --session "[session-id]" fill @e1 "text"      # Fill input
agent-browser --session "[session-id]" type @e1 "text"      # Type without clearing
agent-browser --session "[session-id]" press Enter          # Press key

# Screenshots
agent-browser --session "[session-id]" screenshot "[capture-dir]/[route-id]-[width]x[height]-[state-id]-[iteration]-viewport.png" # Viewport screenshot
agent-browser --session "[session-id]" screenshot --full "[capture-dir]/[route-id]-[width]x[height]-[state-id]-[iteration]-full.png" # Full page screenshot

# Debug evidence
agent-browser --session "[session-id]" console --json > "[capture-dir]/[route-id]-[width]x[height]-[state-id]-[iteration]-console.json" # Console messages, including severity
agent-browser --session "[session-id]" console --clear      # Clear after retaining any earlier evidence
agent-browser --session "[session-id]" errors > "[capture-dir]/[route-id]-[width]x[height]-[state-id]-[iteration]-errors.txt" # Uncaught page errors
agent-browser --session "[session-id]" errors --clear       # Clear before a new route's observation

# Network (API evidence and per-state stubs)
agent-browser --session "[session-id]" network requests --type xhr,fetch    # Captured API requests; failed, aborted, or pending ones mean the state is incomplete
agent-browser --session "[session-id]" network requests --clear             # Clear before a new state's observation
agent-browser --session "[session-id]" network route "<api-pattern>" --body '<json>'  # Stub matching requests (empty or long-content state); cannot set a status code
agent-browser --session "[session-id]" network route "<api-pattern>" --abort          # Abort matching requests (network-failure state)
agent-browser --session "[session-id]" network unroute                      # Remove all stubs before the next state

# Headed mode (visible browser)
agent-browser --session "[session-id]" --headed open "[url]"      # Open with visible browser
agent-browser --session "[session-id]" --headed click @e1         # Click in visible browser

# Wait
agent-browser --session "[session-id]" wait @e1             # Wait for element
agent-browser --session "[session-id]" wait 2000            # Wait milliseconds
```

Allocate `[capture-dir]` as a fresh invocation-owned directory before saving screenshots or logs. Substitute its emitted absolute path literally in later calls. Include a unique route/component ID, exact viewport width and height, interaction state, and iteration in every screenshot and diagnostic filename. Increment the iteration when repeating that combination. Retain every variant for the caller. Record the actual dimensions and state beside each path. A viewport screenshot is not an element crop. Check installed command support against `agent-browser --help` and the [official debug commands](https://agent-browser.dev/commands#debug); mark unavailable log checks unverified instead of reporting zero.

Run each invocation in its own browser session. Generate one ID per invocation, for example `ab-$(date +%s)-$$`, record it as `[session-id]`, and pass `--session "[session-id]"` on every `agent-browser` call, including `close` and the calls in any command or agent that cites this reference. Without it, concurrent commands, agents, and the user share the `default` session, so one invocation's `open` replaces another's page and its `close` ends their browser. Do not rely on `AGENT_BROWSER_SESSION`, because environment variables do not persist between tool calls. Close only the session this invocation created, and do so when the run ends, including after a failed or partial run: `agent-browser --session "[session-id]" close`. Otherwise each run leaves its own daemon and browser alive.

## File-to-Route Mapping

Use these patterns to find routes, then trace each changed component to the regions, dialogs, drawers, or widgets that render it. Track the route, rendering host, and affected state as separate fields because several placements can share a URL. If a tested placement represents omitted equivalents, record which placements it represents and why the changed behavior and layout constraints are equivalent.

| File Pattern | Route(s) |
|-------------|----------|
| `resources/views/users/*` | `/users`, `/users/:id`, `/users/new` |
| `src/controllers/SettingsController.ts` | `/settings` |
| `src/controllers/*.ts` | Pages using that controller |
| `src/components/*.tsx` | Pages rendering that component |
| `src/layouts/*` | All pages (test homepage at minimum) |
| `src/styles/*` | Visual regression on key pages |
| `src/helpers/*.ts` | Pages using that helper |
| `src/app/*` (Next.js) | Corresponding routes |

## Setup

```bash
# Check installation
command -v agent-browser >/dev/null 2>&1 && echo "Installed" || echo "NOT INSTALLED"

# Install if needed
npm install -g agent-browser && agent-browser install
```
