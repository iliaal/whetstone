---
name: ia-reproduce-bug
description: Reproduce a GitHub issue bug with visual evidence (Playwright screenshots, log analysis). Takes a GitHub issue number. For non-issue bug validation, use the bug-reproduction-validator agent.
argument-hint: "[GitHub issue number]"
disable-model-invocation: true
---

**Requires:** Playwright MCP server configured. If unavailable, fall back to manual browser testing with screenshots.

# Reproduce Bug Command

Look at github issue #$ARGUMENTS and read the issue description and comments.

## Phase 1: Log Investigation

Follow the `ia-debugging` skill methodology -- read the error, trace backward, gather evidence.

1. Search the codebase for code paths related to the issue description
2. Check application logs, error tracking, and monitoring for relevant entries
3. Identify the component boundaries involved and where the failure likely occurs

Think about the places it could go wrong. Look for logging output that helps narrow the cause. Keep investigating until you have a clear hypothesis.

## Phase 2: Visual Reproduction with Playwright

**Requires Playwright MCP server.** If not available, skip to Phase 3 with findings from Phase 1 only.

If the bug is UI-related or involves user flows, use Playwright to visually reproduce it:

### Step 1: Verify Server is Running

```
mcp__plugin_compound-engineering_pw__browser_navigate({ url: "http://localhost:3000" })
mcp__plugin_compound-engineering_pw__browser_snapshot({})
```

If server not running, inform user to start their dev server.

### Step 2: Navigate to Affected Area

Based on the issue description, navigate to the relevant page:

```
mcp__plugin_compound-engineering_pw__browser_navigate({ url: "http://localhost:3000/[affected_route]" })
mcp__plugin_compound-engineering_pw__browser_snapshot({})
```

### Step 3: Capture Screenshots

Take screenshots at each step of reproducing the bug:

```
mcp__plugin_compound-engineering_pw__browser_take_screenshot({ filename: "bug-[issue]-step-1.png" })
```

### Step 4: Follow User Flow

Reproduce the exact steps from the issue:

1. **Read the issue's reproduction steps**
2. **Execute each step using Playwright:**
   - `browser_click` for clicking elements
   - `browser_type` for filling forms
   - `browser_snapshot` to see the current state
   - `browser_take_screenshot` to capture evidence

3. **Check for console errors:**
   ```
   mcp__plugin_compound-engineering_pw__browser_console_messages({ level: "error" })
   ```

### Step 5: Capture Bug State

When you reproduce the bug:

1. Take a screenshot of the bug state
2. Capture console errors
3. Document the exact steps that triggered it

```
mcp__plugin_compound-engineering_pw__browser_take_screenshot({ filename: "bug-[issue]-reproduced.png" })
```

## Phase 3: Document Findings

**Reference Collection:**

- [ ] Document all research findings with specific file paths (e.g., `src/services/ExampleService.ts:42`)
- [ ] Include screenshots showing the bug reproduction
- [ ] List console errors if any
- [ ] Document the exact reproduction steps

## Phase 4: Report Back

Add a comment to the issue with:

1. **Findings** - What you discovered about the cause
2. **Reproduction Steps** - Exact steps to reproduce (verified)
3. **Screenshots** - Visual evidence of the bug (upload captured screenshots)
4. **Relevant Code** - File paths and line numbers
5. **Suggested Fix** - If you have one

## Integration

For agent-invocable bug reproduction without a GitHub issue number, use the `ia-bug-reproduction-validator` agent. It validates and classifies bug reports but does not fix them.
