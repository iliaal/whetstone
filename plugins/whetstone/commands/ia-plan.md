---
name: ia-plan
description: Transform feature descriptions into well-structured project plans following conventions
argument-hint: "[feature description, bug report, or improvement idea]"
---

# Create a plan for a new feature or bug fix

Follow the `ia-planning` skill for methodology (file persistence in `.plan/`, phase sizing, context management rules). This command adds structured research, issue templates, and `docs/plans/` output on top of that methodology.

## Introduction

Transform feature descriptions, bug reports, or improvement ideas into well-structured markdown files issues that follow project conventions and best practices. This command provides flexible detail levels to match your needs.

## Feature Description

<feature_description> #$ARGUMENTS </feature_description>

**If the feature description above is empty, ask the user:** "What would you like to plan? Please describe the feature, bug fix, or improvement you have in mind."

Do not proceed until you have a clear feature description from the user.

### 0. Idea Refinement

**Check for brainstorm output first.** Look for recent relevant brainstorms in `docs/brainstorms/`:

```bash
ls -la docs/brainstorms/*.md 2>/dev/null | head -10
```

A brainstorm is relevant if its topic matches the feature description, created within the last 14 days, and (if multiple match) prefer the most recent.

**If a relevant brainstorm exists:** Read it thoroughly, announce "Found brainstorm from [date]: [topic]. Using as foundation." and carry forward all decisions, constraints, success criteria, and technical choices into the plan. Skip baseline idea refinement and run a gap-analysis interview focused only on implementation concerns the brainstorm didn't cover (deployment/rollback, monitoring, data migration, performance, security at the implementation level). The brainstorm is the origin document — reference it with `(see brainstorm: docs/brainstorms/<filename>)` throughout the plan and scan each brainstorm section before finalizing to verify nothing was dropped.

If multiple brainstorms could match, use `AskUserQuestion` to ask which to use.

**If no brainstorm found (or not relevant):** Run idea refinement using the `ia-brainstorming` skill's Phase 1 interview protocol and the deep interview protocol in CLAUDE.md. Use `AskUserQuestion` for all prompts. Continue until the idea is clear OR the user says "proceed."

**Gather signals for the research decision** during refinement: user familiarity with the codebase, intent (speed vs thoroughness), topic risk (security/payments/external APIs warrant more caution), and uncertainty level.

**Skip option:** If the feature description is already detailed, offer: "Your description is clear. Should I proceed with research, or refine further?"

## Main Tasks

### 1. Local Research (Always Runs - Parallel)

<thinking>
First, I need to understand the project's conventions, existing patterns, and any documented learnings. This is fast and local - it informs whether external research is needed.
</thinking>

Run these agents **in parallel** to gather local context:

- Task ia-repo-research-analyst(feature_description)
- Task ia-learnings-researcher(feature_description)

**What to look for:**
- **Repo research:** existing patterns, CLAUDE.md guidance, technology familiarity, pattern consistency
- **Learnings:** documented solutions in `docs/solutions/` that might apply (gotchas, patterns, lessons learned)

These findings inform the next step.

### 1.5. Research Decision

Based on signals from Step 0 and findings from Step 1, decide on external research.

**High-risk topics → always research.** Security, payments, external APIs, data privacy. The cost of missing something is too high. This takes precedence over speed signals.

**Strong local context → skip external research.** Codebase has good patterns, CLAUDE.md has guidance, user knows what they want. External research adds little value.

**Uncertainty or unfamiliar territory → research.** User is exploring, codebase has no examples, new technology. External perspective is valuable.

**Announce the decision and proceed.** Brief explanation, then continue. User can redirect if needed.

Examples:
- "Your codebase has solid patterns for this. Proceeding without external research."
- "This involves payment processing, so I'll research current best practices first."

### 1.5b. External Research (Conditional)

**Only run if Step 1.5 indicates external research is valuable.**

Run these agents in parallel:

- Task ia-best-practices-researcher(feature_description)

### 1.6. Consolidate Research

After all research steps complete, consolidate findings:

- Document relevant file paths from repo research (e.g., `src/services/ExampleService.ts:42`)
- **Include relevant institutional learnings** from `docs/solutions/` (key insights, gotchas to avoid)
- Note external documentation URLs and best practices (if external research was done)
- List related issues or PRs discovered
- Capture CLAUDE.md conventions

**Optional validation:** Briefly summarize findings and ask if anything looks off or missing before proceeding to planning.

### 2. Plan Structure & Naming

Draft a clear, searchable title using conventional format (`feat:`, `fix:`, `refactor:`) and convert it to a filename: `YYYY-MM-DD-<type>-<kebab-case-title>-plan.md`. Keep the descriptive portion 3-5 words so plans are findable by context.

Example: `feat: Add User Authentication` → `2026-01-21-feat-add-user-authentication-plan.md`

Choose the detail level in Step 4 based on scope. The `ia-planning` skill's Plan Template owns the section structure — do not restate sections here.

### 3. SpecFlow Analysis

After planning the issue structure, run SpecFlow Analyzer to validate and refine the feature specification:

- Task ia-spec-flow-analyzer(feature_description, research_findings)

**SpecFlow Analyzer Output:**

- [ ] Review SpecFlow analysis results
- [ ] Incorporate any identified gaps or edge cases into the issue
- [ ] Update acceptance criteria based on SpecFlow findings

### 4. Choose Implementation Detail Level

Select how comprehensive the plan should be. Simpler is mostly better.

| Level | Best for | Includes |
|-------|----------|----------|
| **MINIMAL** | Simple bugs, small improvements | Problem statement, acceptance criteria, context |
| **MORE** | Most features, complex bugs | + technical considerations, success metrics, dependencies |
| **A LOT** | Major features, architectural changes | + phased implementation, alternatives, risk analysis, resource requirements |

See [plan-templates.md](./references/plan-templates.md) for the full template of each level.

### 5. Issue Creation & Formatting

Format the issue content following [issue-formatting.md](./references/issue-formatting.md) (content structure, cross-referencing, code examples, AI-era considerations).

### 6. Final Review & Submission

**Brainstorm cross-check (if plan originated from a brainstorm):**

Before finalizing, re-read the brainstorm document and verify:
- [ ] Every key decision from the brainstorm is reflected in the plan
- [ ] The chosen approach matches what was decided in the brainstorm
- [ ] Constraints and requirements from the brainstorm are captured in acceptance criteria
- [ ] Open questions from the brainstorm are either resolved or flagged
- [ ] The `origin:` frontmatter field points to the brainstorm file
- [ ] The Sources section includes the brainstorm with a summary of carried-forward decisions

**Pre-submission Checklist:**

- [ ] Title is searchable and descriptive
- [ ] Labels accurately categorize the issue
- [ ] All template sections are complete
- [ ] Links and references are working
- [ ] Acceptance criteria are measurable
- [ ] Add names of files in pseudo code examples and todo lists
- [ ] Add an ERD mermaid diagram if applicable for new model changes

## Write Plan File

**REQUIRED: Write the plan file to disk before presenting any options.**

```bash
mkdir -p docs/plans/
```

Use the Write tool to save the complete plan to `docs/plans/YYYY-MM-DD-<type>-<descriptive-name>-plan.md`. This step is mandatory and cannot be skipped -- even when running as part of LFG or other automated pipelines.

Confirm: "Plan written to docs/plans/[filename]"

**Pipeline mode:** If invoked from an automated workflow (LFG or any `disable-model-invocation` context), skip all AskUserQuestion calls. Make decisions automatically and proceed to writing the plan without interactive prompts.

## Output Format

**Filename:** Use the date and kebab-case filename from Step 2 Title & Categorization.

```
docs/plans/YYYY-MM-DD-<type>-<descriptive-name>-plan.md
```

Examples:
- ✅ `docs/plans/2026-01-15-feat-user-authentication-flow-plan.md`
- ✅ `docs/plans/2026-02-03-fix-checkout-race-condition-plan.md`
- ✅ `docs/plans/2026-03-10-refactor-api-client-extraction-plan.md`
- ❌ `docs/plans/2026-01-15-feat-thing-plan.md` (not descriptive - what "thing"?)
- ❌ `docs/plans/2026-01-15-feat-new-feature-plan.md` (too vague - what feature?)
- ❌ `docs/plans/2026-01-15-feat: user auth-plan.md` (invalid characters - colon and space)
- ❌ `docs/plans/feat-user-auth-plan.md` (missing date prefix)

## Post-Generation Options

After writing the plan file, use the **AskUserQuestion tool** to present these options:

**Question:** "Plan ready at `docs/plans/YYYY-MM-DD-<type>-<name>-plan.md`. What would you like to do next?"

**Options:**
1. **Open plan in editor** - Open the plan file for review
2. **Run `/ia-deepen-plan`** - Enhance each section with parallel research agents (best practices, performance, UI)
3. **Run `/ia-review`** - Technical feedback from code-focused reviewers (Kieran, Simplicity)
4. **Review and refine** - Improve the document through structured self-review
5. **Start `/ia-work`** - Begin implementing this plan locally
6. **Start `/ia-work` on remote** - Begin implementing in Claude Code on the web (use `&` to run in background)
7. **Create Issue** - Create issue in project tracker (GitHub/Linear)

Based on selection:
- **Open plan in editor** → Run `open docs/plans/<plan_filename>.md` to open the file in the user's default editor
- **`/ia-deepen-plan`** → Call the /ia-deepen-plan command with the plan file path to enhance with research
- **`/ia-review`** → Call the /ia-review command with the plan file path
- **Review and refine** → Load `ia-document-review` skill.
- **`/ia-work`** → Call the /ia-work command with the plan file path
- **`/ia-work` on remote** → Run `/ia-work docs/plans/<plan_filename>.md &` to start work in background for Claude Code web
- **Create Issue** → See "Issue Creation" section below
- **Other** (automatically provided) → Accept free text for rework or specific changes

**Note:** If running `/ia-plan` with ultrathink enabled, automatically run `/ia-deepen-plan` after plan creation for maximum depth and grounding.

Loop back to options after Simplify or Other changes until user selects `/ia-work` or `/ia-review`.

## Issue Creation

Follow the issue creation procedure in [issue-formatting.md](./references/issue-formatting.md#issue-creation) (tracker detection, GitHub/Linear commands).

NEVER CODE! Just research and write the plan.
