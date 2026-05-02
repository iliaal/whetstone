---
name: ia-setup
description: >-
  Diagnose the whetstone environment and configure review agents.
  Checks CLI dependencies and plugin version, then runs the review-agent wizard
  that writes whetstone.local.md. Use when onboarding a project,
  troubleshooting missing tools, or configuring review agents.
disable-model-invocation: true
---

# Compound Engineering Setup

Two phases: diagnose the environment, then configure review agents for `/ia-review` and `/ia-work`.

## Phase 1: Diagnose

### Step 1: Determine Plugin Version

Read `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json` if available and extract `version`. Pass it to the health check via `--version`. If the file or the field is missing, omit the flag.

### Step 2: Run the Health Check Script

Before running, display: "Compound Engineering -- checking your environment..."

Run the bundled script. Do not perform manual dependency checks -- the script handles CLI probes, alt-name resolution, and install hints in one pass.

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/check-health.sh --version VERSION
```

Or without version if Step 1 could not determine it:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/check-health.sh
```

Display the script's output to the user verbatim.

### Step 3: Evaluate Results

Parse the output. Two possible states:

- **All clear** (`✅ All clear` line): proceed to Phase 2.
- **Issues found** (`⚠️ N issue(s) found`): proceed to Step 4.

### Step 4: Offer Installation for Missing Tools

The script prints the recommended install command under each missing tool. Present the missing tools to the user using `AskUserQuestion` (load the schema via `ToolSearch` with `select:AskUserQuestion` if not already loaded) as a multiSelect with all items pre-selected. Use the install command from the script output as the description.

For each selected tool, in order:

1. Show the install command and ask for approval using `AskUserQuestion`:

   ```
   question: "Install <tool>?"
   header: "Install"
   options:
     - label: "Run this command (Recommended)"
       description: "<command from script output>"
     - label: "Skip"
       description: "I'll install manually"
   ```

2. If approved, run the command via `Bash`. After it completes, verify with `command -v <tool>`.
3. If verification succeeds, report success.
4. If verification fails, display the upstream URL from the script output as fallback and continue to the next tool.

After the install loop, re-run `check-health.sh` once and show the updated report.

## Phase 2: Configure Review Agents

### Step 5: Check Existing Review Config

Read `whetstone.local.md` in the project root (use `git rev-parse --show-toplevel` to resolve it). If it exists, display the current `review_agents` list and use `AskUserQuestion`:

```
question: "Review config already exists. What would you like to do?"
header: "Config"
options:
  - label: "Keep current"
    description: "Leave whetstone.local.md unchanged"
  - label: "Reconfigure"
    description: "Run the interactive wizard again"
  - label: "View"
    description: "Show the file contents, then stop"
```

If "View": read and display the file, then stop.
If "Keep current": stop.

### Step 6: Detect Stack

Auto-detect the project stack:

```bash
test -f tsconfig.json && echo "typescript" || \
test -f package.json && echo "javascript" || \
test -f pyproject.toml && echo "python" || \
test -f requirements.txt && echo "python" || \
test -f composer.json && echo "php" || \
echo "general"
```

### Step 7: Ask Mode

Use `AskUserQuestion`:

```
question: "Detected {type} project. How would you like to configure?"
header: "Setup"
options:
  - label: "Auto-configure (Recommended)"
    description: "Use smart defaults for {type}. Done in one click."
  - label: "Customize"
    description: "Choose stack, focus areas, and review depth."
```

### Step 8: Auto Defaults (if Auto)

Skip to Step 10 with these defaults:

- **Python/TypeScript:** `[ia-kieran-reviewer, ia-code-simplicity-reviewer, ia-security-sentinel, ia-performance-oracle]`
- **PHP:** `[ia-code-simplicity-reviewer, ia-security-sentinel, ia-performance-oracle, ia-architecture-strategist]`
- **General:** `[ia-code-simplicity-reviewer, ia-security-sentinel, ia-performance-oracle, ia-architecture-strategist]`

### Step 9: Customize (if Customize)

**a. Stack** -- confirm or override (only show options that differ from the detected type):

```
question: "Which stack should we optimize for?"
header: "Stack"
options:
  - label: "{detected_type} (Recommended)"
    description: "Auto-detected from project files"
  - label: "Python"
    description: "Python -- adds Pythonic pattern reviewer"
  - label: "TypeScript"
    description: "TypeScript -- adds type safety reviewer"
  - label: "PHP"
    description: "PHP/Laravel -- adds PHP-specific reviewer"
```

**b. Focus areas** -- multiSelect:

```
question: "Which review areas matter most?"
header: "Focus"
multiSelect: true
options:
  - label: "Security"
    description: "Vulnerability scanning, auth, input validation (ia-security-sentinel)"
  - label: "Performance"
    description: "N+1 queries, memory leaks, complexity (ia-performance-oracle)"
  - label: "Architecture"
    description: "Design patterns, SOLID, separation of concerns (ia-architecture-strategist)"
  - label: "Code simplicity"
    description: "Over-engineering, YAGNI violations (ia-code-simplicity-reviewer)"
```

**c. Depth:**

```
question: "How thorough should reviews be?"
header: "Depth"
options:
  - label: "Thorough (Recommended)"
    description: "Stack reviewers + all selected focus agents."
  - label: "Fast"
    description: "Stack reviewers + code simplicity only. Less context, quicker."
  - label: "Comprehensive"
    description: "All above + git history, data integrity, agent-native checks."
```

### Step 10: Build Agent List and Write File

**Stack-specific agents:**
- Python/TypeScript → `ia-kieran-reviewer`
- PHP → (none; rely on focus agents)
- General → (none)

**Focus area agents:**
- Security → `ia-security-sentinel`
- Performance → `ia-performance-oracle`
- Architecture → `ia-architecture-strategist`
- Code simplicity → `ia-code-simplicity-reviewer`

**Depth:**
- Thorough: stack + selected focus areas
- Fast: stack + `ia-code-simplicity-reviewer` only
- Comprehensive: all above + `ia-git-history-analyzer, ia-database-guardian`

Write `whetstone.local.md` at the repo root:

```markdown
---
review_agents: [{computed agent list}]
---

# Review Context

Add project-specific review instructions here.
These notes are passed to all review agents during /ia-review and /ia-work.

Examples:
- "We use event sourcing -- check for missed projections"
- "Our API is public -- extra scrutiny on input validation"
- "Performance-critical: we serve 10k req/s on this endpoint"
```

### Step 11: Confirm

```
✅ Compound Engineering setup complete

   Tools:        {n}/{total} installed
   Stack:        {type}
   Review depth: {depth}
   Agents:       {count} configured
                 {agent list, one per line}

Tip: Edit the "Review Context" section of whetstone.local.md to add
     project-specific instructions. Re-run /ia-setup anytime to reconfigure.
```
