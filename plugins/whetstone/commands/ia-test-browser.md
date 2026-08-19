---
name: ia-test-browser
description: Run browser tests on pages affected by current PR or branch
argument-hint: "[PR number, branch name, or 'current' for current branch]"
---

# Browser Test Command

<command_purpose>Run end-to-end browser tests on pages affected by a PR or branch changes using agent-browser CLI.</command_purpose>

## CRITICAL: Use agent-browser CLI Only

**DO NOT use Chrome MCP tools (mcp__claude-in-chrome__*).**

This command uses the `agent-browser` CLI exclusively. The agent-browser CLI is a Bash-based tool from Vercel that runs headless Chromium. It is NOT the same as Chrome browser automation via MCP.

If you find yourself calling `mcp__claude-in-chrome__*` tools, STOP. Use `agent-browser` Bash commands instead.

## Introduction

<role>QA Engineer specializing in browser-based end-to-end testing</role>

This command tests affected pages in a real browser, catching issues that unit tests miss:
- JavaScript integration bugs
- CSS/layout regressions
- User workflow breakages
- Console errors

## Prerequisites

<requirements>
- Local development server running (e.g., `npm run dev`, `php artisan serve`)
- agent-browser CLI installed (see [references/agent-browser-cli.md](references/agent-browser-cli.md))
- Git repository with changes to test
</requirements>

## Setup

For agent-browser install/verify steps and the full command reference, see [references/agent-browser-cli.md](references/agent-browser-cli.md). Step 0 below performs the runtime install check.

## Main Tasks

### 0. Verify agent-browser Installation

Before starting ANY browser testing, verify agent-browser is installed:

```bash
command -v agent-browser >/dev/null 2>&1 && echo "Ready" || (echo "Installing..." && npm install -g agent-browser && agent-browser install)
```

If installation fails, inform the user and stop.

### 1. Ask Browser Mode

<ask_browser_mode>

Before starting tests, ask user if they want to watch the browser:

Use AskUserQuestion with:
- Question: "Do you want to watch the browser tests run?"
- Options:
  1. **Headed (watch)** - Opens visible browser window so you can see tests run
  2. **Headless (faster)** - Runs in background, faster but invisible

Store the choice and use `--headed` flag when user selects "Headed".

</ask_browser_mode>

### 2. Determine Test Scope

<test_target> $ARGUMENTS </test_target>

<determine_scope>

**If PR number provided:**
```bash
gh pr view [number] --json files -q '.files[].path'
```

**If 'current' or empty:**
```bash
git diff --name-only main...HEAD
```

**If branch name provided:**
```bash
git diff --name-only main...[branch]
```

</determine_scope>

### 3. Map Files to Routes

<file_to_route_mapping>

Map changed files to testable routes using the file-to-route table in [references/agent-browser-cli.md](references/agent-browser-cli.md).

Build a list of URLs to test based on the mapping.

</file_to_route_mapping>

### 4. Verify Server is Running

<check_server>

Resolve the dev-server port rather than assuming 3000 -- Vite and SvelteKit default to 5173, and a `PORT=` in `.env` or a `--port` flag in a package.json script overrides either. Each fenced block below runs as its own shell, so the two resolution lines are repeated in every block that uses `$BASE_URL`; a bare `$BASE_URL` carried across a block boundary expands to empty and silently navigates to a relative path.

Verify the local server is accessible:

```bash
PORT=$(bash ${CLAUDE_PLUGIN_ROOT}/commands/scripts/resolve-dev-port)
BASE_URL="http://localhost:$PORT"
agent-browser open "$BASE_URL"
agent-browser snapshot -i
```

If server is not running, inform user:
```markdown
**Server not running**

Please start your development server:
- Node/Next.js: `npm run dev`
- PHP: `php artisan serve`

Then run `/ia-test-browser` again.
```

</check_server>

### 5. Test Each Affected Page

<test_pages>

For each affected route, use agent-browser CLI commands (NOT Chrome MCP):

**Step 1: Navigate and capture snapshot**
```bash
PORT=$(bash ${CLAUDE_PLUGIN_ROOT}/commands/scripts/resolve-dev-port)
BASE_URL="http://localhost:$PORT"
agent-browser open "$BASE_URL/[route]"
agent-browser snapshot -i
```

**Step 2: For headed mode (visual debugging)**
```bash
PORT=$(bash ${CLAUDE_PLUGIN_ROOT}/commands/scripts/resolve-dev-port)
BASE_URL="http://localhost:$PORT"
agent-browser --headed open "$BASE_URL/[route]"
agent-browser --headed snapshot -i
```

**Step 3: Verify key elements**
- Use `agent-browser snapshot -i` to get interactive elements with refs
- Page title/heading present
- Primary content rendered
- No error messages visible
- Forms have expected fields

**Step 4: Test critical interactions**
```bash
agent-browser click @e1  # Use ref from snapshot
agent-browser snapshot -i
```

**Step 5: Take screenshots**
```bash
agent-browser screenshot page-name.png
agent-browser screenshot --full page-name-full.png  # Full page
```

</test_pages>

### 6. Human Verification (When Required)

<human_verification>

Pause for human input when testing touches:

| Flow Type | What to Ask |
|-----------|-------------|
| OAuth | "Please sign in with [provider] and confirm it works" |
| Email | "Check your inbox for the test email and confirm receipt" |
| Payments | "Complete a test purchase in sandbox mode" |
| SMS | "Verify you received the SMS code" |
| External APIs | "Confirm the [service] integration is working" |

Use AskUserQuestion:
```markdown
**Human Verification Needed**

This test touches the [flow type]. Please:
1. [Action to take]
2. [What to verify]

Did it work correctly?
1. Yes - continue testing
2. No - describe the issue
```

</human_verification>

### 7. Handle Failures

<failure_handling>

When a test fails:

1. **Document the failure:**
   - Screenshot the error state: `agent-browser screenshot error.png`
   - Note the exact reproduction steps

2. **Ask user how to proceed:**
   ```markdown
   **Test Failed: [route]**

   Issue: [description]
   Console errors: [if any]

   How to proceed?
   1. Fix now - I'll help debug and fix
   2. Create todo - Add to todos/ for later
   3. Skip - Continue testing other pages
   ```

3. **If "Fix now":**
   - Investigate the issue
   - Propose a fix
   - Apply fix
   - Re-run the failing test

4. **If "Create todo":**
   - Create `{id}-pending-p1-browser-test-{description}.md`
   - Continue testing

5. **If "Skip":**
   - Log as skipped
   - Continue testing

</failure_handling>

### 8. Test Summary

<test_summary>

After all tests complete, present summary:

```markdown
## Browser Test Results

**Test Scope:** PR #[number] / [branch name]
**Server:** [base-url]

### Pages Tested: [count]

| Route | Status | Notes |
|-------|--------|-------|
| `/users` | Pass | |
| `/settings` | Pass | |
| `/dashboard` | Fail | Console error: [msg] |
| `/checkout` | Skip | Requires payment credentials |

### Console Errors: [count]
- [List any errors found]

### Human Verifications: [count]
- OAuth flow: Confirmed
- Email delivery: Confirmed

### Failures: [count]
- `/dashboard` - [issue description]

### Created Todos: [count]
- `005-pending-p1-browser-test-dashboard-error.md`

### Result: [PASS / FAIL / PARTIAL]
```

</test_summary>

## Quick Usage Examples

```bash
# Test current branch changes
/ia-test-browser

# Test specific PR
/ia-test-browser 847

# Test specific branch
/ia-test-browser feature/new-dashboard
```

## agent-browser CLI Reference

See [references/agent-browser-cli.md](references/agent-browser-cli.md) for the full command reference, file-to-route mapping, and setup instructions.

**ALWAYS use agent-browser Bash commands. NEVER use mcp__claude-in-chrome__* tools.**
