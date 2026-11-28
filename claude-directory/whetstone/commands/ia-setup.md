---
description: "Diagnose the whetstone environment and configure review agents. Checks CLI dependencies, then runs the review-agent wizard that writes whetstone.local.md. Use when onboarding a project, troubleshooting missing tools, or configuring review agents."
disable-model-invocation: true
---

# Compound Engineering Setup

Two phases: diagnose the environment, then configure review agents for `/ia-review` and `/ia-work`.

## Phase 1: Diagnose

### Steps 1-2: Probe Tools

Before probing, display: "Compound Engineering -- checking your environment..."

Probe each tool with `command -v <tool>` (for `python3`, also accept `python`) and report the result as a table:

| Tool | Need | Install guidance |
|---|---|---|
| `bash` 4.4+ | recommended | https://www.gnu.org/software/bash/ |
| `git` | recommended | https://git-scm.com/downloads |
| `gh` | recommended | https://cli.github.com |
| `jq` | recommended | https://jqlang.github.io/jq/ |
| `python3` | recommended | https://www.python.org/downloads/ |
| `node`, `npm` | optional | https://nodejs.org |
| `playwright` | optional | https://playwright.dev/python |

For Bash, run `bash -c 'echo "${BASH_VERSINFO[0]}.${BASH_VERSINFO[1]}"'` and require 4.4 or newer from the Bash that PATH selects.

### Steps 3-4: Offer Installation for Missing Tools

When every recommended tool is present, proceed to Phase 2. Otherwise, list the missing tools and their install guidance. Never execute a URL as a shell command. When the user asks for help with a tool, read its upstream instructions, determine a concrete command for the current platform, and show it for approval through `AskUserQuestion` (load the schema via `ToolSearch` with `select:AskUserQuestion` if not already loaded) before running it. After an approved install, verify with `command -v <tool>`; on failure, show the upstream URL and continue. Report unresolved tools and the capabilities they affect, then continue to Phase 2.

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
If "Reconfigure": retain the full existing file as the edit baseline. Preserve its other frontmatter fields and all body content through Step 10.

### Step 6: Detect Stack

Auto-detect the project stack:

```bash
if [[ -f tsconfig.json ]]; then
  echo "typescript"
elif [[ -f package.json ]]; then
  echo "javascript"
elif [[ -f pyproject.toml || -f requirements.txt ]]; then
  echo "python"
elif [[ -f composer.json ]]; then
  echo "php"
else
  echo "general"
fi
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
- **JavaScript/PHP/General:** `[ia-code-simplicity-reviewer, ia-security-sentinel, ia-performance-oracle, ia-architecture-strategist]`

### Step 9: Customize (if Customize)

**a. Stack**: confirm or override (only show options that differ from the detected type):

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
    description: "PHP/Laravel -- uses the selected focus reviewers"
```

**b. Focus areas**: multiSelect:

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
    description: "All above + git history, data integrity."
```

### Step 10: Build Agent List and Write File

**Stack-specific agents:**
- Python/TypeScript → `ia-kieran-reviewer`
- JavaScript/PHP/General → selected focus agents only

**Focus area agents:**
- Security → `ia-security-sentinel`
- Performance → `ia-performance-oracle`
- Architecture → `ia-architecture-strategist`
- Code simplicity → `ia-code-simplicity-reviewer`

**Depth:**
- Thorough: stack + selected focus areas
- Fast: stack + `ia-code-simplicity-reviewer` only
- Comprehensive: all above + `ia-git-history-analyzer, ia-database-guardian`

If `whetstone.local.md` exists, edit only the `review_agents` field in its YAML frontmatter. Preserve every other field, comment, and body section, including Review Context. Add the field if absent. If the frontmatter cannot be safely parsed or the field is duplicated, report the conflict before writing. Compare the exact diff with the baseline; only the selected agent configuration may change.

If the file does not exist, create `whetstone.local.md` at the repo root using this template:

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
Compound Engineering setup complete

   Tools:        {n}/{total} installed
   Stack:        {type}
   Review depth: {depth}
   Agents:       {count} configured
                 {agent list, one per line}

Tip: Edit the "Review Context" section of whetstone.local.md to add
     project-specific instructions. Re-run /ia-setup anytime to reconfigure.
```
