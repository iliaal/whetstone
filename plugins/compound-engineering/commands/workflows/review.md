---
name: workflows:review
description: Perform exhaustive code reviews using multi-agent analysis, ultra-thinking, and worktrees
argument-hint: "[PR number, GitHub URL, branch name, or latest]"
---

# Review Command

Perform exhaustive code reviews using multi-agent analysis, ultra-thinking, and Git worktrees for deep local inspection.

## Introduction

**Senior Code Review Architect** with expertise in security, performance, architecture, and quality assurance.

## Prerequisites

- Git repository with GitHub CLI (`gh`) installed and authenticated
- Clean main/master branch
- Proper permissions to create worktrees and access the repository
- For document reviews: Path to a markdown file or document

## Main Tasks

### 1. Determine Review Target & Setup (ALWAYS FIRST)

**Review target:** #$ARGUMENTS

First, determine the review target type and set up the code for analysis.

#### Immediate Actions:

- [ ] Determine review type: PR number (numeric), GitHub URL, file path (.md), or empty (current branch)
- [ ] Check current git branch
- [ ] If ALREADY on the target branch (PR branch, requested branch name, or the branch already checked out for review) → proceed with analysis on current branch
- [ ] If DIFFERENT branch than the review target → offer to use worktree: "Use git-worktree skill for isolated Call `skill: git-worktree` with branch name
- [ ] Fetch PR metadata using `gh pr view --json` for title, body, files, linked issues
- [ ] Set up language-specific analysis tools
- [ ] Prepare security scanning environment
- [ ] Make sure we are on the branch we are reviewing. Use gh pr checkout to switch to the branch or manually checkout the branch.

Ensure that the code is ready for analysis (either in worktree or on current branch). ONLY then proceed to the next step.

#### Scope Resolution

When no specific files are given (e.g., a bare branch name or the PR has no file list yet), resolve scope via this fallback chain:
1. User-specified files/directories (explicit request)
2. Session-modified files (`git diff --name-only` for unstaged + staged)
3. All uncommitted files (`git diff --name-only HEAD`)
4. Untracked files (`git ls-files --others --exclude-standard`)
5. **Zero files → stop.** Ask what to review.

Exclude lockfiles, minified/bundled output, and vendored/generated code.

#### Two-Stage Review Gate

The review proceeds in two stages. Do NOT skip to code quality before spec compliance passes.

**Stage 1 -- Spec compliance (MUST complete before Stage 2):**
- Compare the diff against the PR description, linked issue, or task spec.
- Run a Scope Drift Check: `git diff --stat` against the PR's stated intent. Classify as **CLEAN** / **DRIFT DETECTED** / **REQUIREMENTS MISSING**.
  - DRIFT DETECTED: note drifted files and ask the author -- ship as-is, split the PR, or remove unrelated changes?
  - REQUIREMENTS MISSING: list what the spec promises but the diff doesn't deliver.
- Flag missing requirements, unnecessary additions, and interpretation gaps.
- If the implementation is fundamentally wrong (solves the wrong problem), stop here. Report Stage 1 failure and skip Stage 2 -- reviewing code quality on the wrong feature wastes effort.

**Stage 2 -- Code quality:** Only after Stage 1 passes, proceed to the parallel agent dispatch and ultra-thinking phases below.

#### Protected Artifacts

The following paths are compound-engineering pipeline artifacts and must never be flagged for deletion, removal, or gitignore by any review agent:

- `docs/plans/*.md` -- Plan files created by `/workflows:plan`. These are living documents that track implementation progress (checkboxes are checked off by `/workflows:work`).
- `docs/solutions/*.md` -- Solution documents created during the pipeline.

If a review agent flags any file in these directories for cleanup or removal, discard that finding during synthesis. Do not create a todo for it.

#### Load Review Agents

Read `compound-engineering.local.md` in the project root. If found, use `review_agents` from YAML frontmatter. If the markdown body contains review context, pass it to each agent as additional instructions.

If no settings file exists, run `/setup` to create one. Then read the newly created file and continue.

#### Parallel Agents to review the PR:

Dispatch all configured review agents in a SINGLE assistant message containing one Task tool call per agent. Do NOT issue them across multiple messages -- that serializes what should run concurrently. For each agent in the `review_agents` list:

```
Task {agent-name}(PR content + review context from settings body)
```

Additionally, always run these regardless of settings:
- Task learnings-researcher(PR content) - Search docs/solutions/ for past issues related to this PR's modules and patterns

#### Per-agent artifact persistence

For large reviews -- 8+ agents OR diff with more than 500 changed lines (added + deleted, per `git diff --shortstat`) -- persist each agent's output to a numbered file under `.review/` in the working directory:

```
.review/
├── 01-security-sentinel.md
├── 02-performance-oracle.md
├── 03-architecture-strategist.md
├── 04-correctness.md
└── ...
```

At the start of synthesis (section 3 below), read each `.review/NN-*.md` file fresh rather than relying on prior message context. This survives compaction between dispatch and synthesis on large reviews -- main context can lose specialist outputs when the window fills, and rebuilding from file is deterministic where re-running specialists is not.

**Missing-file recovery**: before synthesis, list `.review/NN-*.md`. If any expected file is missing or empty (e.g., a specialist agent crashed or timed out mid-run), re-dispatch that specific agent before proceeding — silently missing a specialist loses coverage in the synthesis and nobody notices.

**Lifecycle**: `.review/` is transient scratch state, NOT a Protected Artifact like `docs/plans/` or `docs/solutions/`. Add `.review/` to `.gitignore` (or project root `.gitignore`). Delete `.review/` when the review completes (success or abandoned).

Skip this step on small reviews (≤ 7 agents AND ≤ 500 changed lines) -- the filesystem overhead isn't justified when prior outputs fit comfortably in context.

**Red-team adversarial pass (runs last, after all parallel specialists return):**

- Task security-sentinel(PR content + consolidated findings so far + "Run the Adversarial Pass section from your agent definition. Target gaps in the other specialists' coverage -- cross-category compounds, happy-path assumptions, silent failures, trust boundary violations.")

This runs AFTER the parallel pass so it can target the gaps in the specialists' coverage rather than duplicate their work. The detailed red-team methodology lives in the `security-sentinel` agent's Adversarial Pass section.

#### Conditional Agents (Run if applicable):

These agents are run ONLY when the PR matches specific criteria. Check the PR files list to determine if they apply:

**MIGRATIONS: If PR contains database migrations, schema definitions, or data backfills:**

- Task database-guardian(PR content) - Validates ID mappings match production, checks for swapped values, verifies rollback safety
- Task deployment-verification-agent(PR content) - Creates Go/No-Go deployment checklist with SQL verification queries

**When to run:**
- PR includes files matching `database/migrations/*` or schema definition files
- PR modifies columns that store IDs, enums, or mappings
- PR includes data backfill scripts or migration scripts
- PR title/body mentions: migration, backfill, data transformation, ID mapping

**What these agents check:**
- `database-guardian`: Verifies hard-coded mappings match production reality (prevents swapped IDs), checks for orphaned associations, validates dual-write patterns
- `deployment-verification-agent`: Produces executable pre/post-deploy checklists with SQL queries, rollback procedures, and monitoring plans

### 2. Simplification and minimalism review

Run the Task code-simplicity-reviewer() to see if we can simplify the code. Note: `code-simplicity-reviewer` always runs here -- exclude it from `review_agents` in `compound-engineering.local.md` to avoid running it twice.

### 3. Findings synthesis and todo creation

**ALL findings MUST be stored in the todos/ directory using the file-todos skill.** Create todo files immediately after synthesis -- do NOT present findings for user approval first. Use the skill for structured todo management.

#### Step 1: Synthesize All Findings

Consolidate all agent reports into a categorized list of findings. Remove duplicates, prioritize by severity and impact.

- [ ] Collect findings from all parallel agents
- [ ] Surface learnings-researcher results: if past solutions are relevant, flag them as "Known Pattern" with links to docs/solutions/ files
- [ ] Discard any findings that recommend deleting or gitignoring files in `docs/plans/` or `docs/solutions/` (see Protected Artifacts above)
- [ ] Categorize by type: security, performance, architecture, quality, etc.
- [ ] Assign severity levels using the `code-review` skill's four-level scale: **Critical** (blocks merge), **Important** (should fix before merge), **Medium** (should fix, non-blocking), **Minor** (optional). Treat legacy `P1`/`P2`/`P3` aliases as Critical/Important/Medium respectively.
- [ ] Assign sequential `CR-001`, `CR-002`... IDs across all severities so findings can be referenced by ID in PR threads and follow-up todos
- [ ] Deduplicate using the merge algorithm from `code-review` skill (Merge Algorithm section): same file:line + same issue = merge with higher severity; same file:line + different issue = keep both tagged "co-located"; conflicting severity = take the higher; conflicting recommendations = mark `NEEDS DECISION` and present both; convergence (3+ agents agree) = boost confidence by 0.1
- [ ] Surface red-team findings separately in the summary under a "Cross-cutting / adversarial" heading so reviewers see what the parallel specialists missed
- [ ] Estimate effort for each finding (Small/Medium/Large)

#### Step 2: Create Todo Files

Create todo files for ALL findings immediately using the `file-todos` skill. Do not present findings one-by-one for user approval -- create all todos, then summarize.

For large PRs (15+ findings), launch parallel sub-agents grouped by severity (one per P1/P2/P3 batch) -- all sub-agent Task calls issued in a single message, not one message per batch. Always add `code-review` tag plus relevant domain tags (`security`, `performance`, `architecture`, etc.).

#### Step 3: Summary Report

After creating all todo files, present comprehensive summary:

````markdown
## ✅ Code Review Complete

**Review Target:** PR #XXXX - [PR Title] **Branch:** [branch-name]

### Findings Summary:

- **Total Findings:** [X]
- **Critical:** [count] - BLOCKS MERGE
- **Important:** [count] - Should fix before merge
- **Medium:** [count] - Should fix, non-blocking
- **Minor:** [count] - Optional

### Created Todo Files:

**Critical (BLOCKS MERGE):**

- `001-pending-critical-{finding}.md` - {description}
- `002-pending-critical-{finding}.md` - {description}

**Important:**

- `003-pending-important-{finding}.md` - {description}
- `004-pending-important-{finding}.md` - {description}

**Medium:**

- `005-pending-medium-{finding}.md` - {description}

### Review Agents Used:

- security-sentinel
- performance-oracle
- architecture-strategist
- [other agents]

### Next Steps:

1. **Address Critical Findings**: must be fixed before merge

   - Review each Critical todo in detail
   - Implement fixes or request exemption
   - Verify fixes before merging PR

2. **Triage All Todos**:
   ```bash
   ls todos/*-pending-*.md  # View all pending todos
   /triage                  # Use slash command for interactive triage
   ```
````

3. **Work on Approved Todos**:

   ```bash
   /resolve-todo-parallel  # Fix all approved items efficiently
   ```

4. **Track Progress**:
   - Rename file when status changes: pending → ready → complete
   - Update Work Log as you work
   - Commit todos: `git add todos/ && git commit -m "refactor: add code review findings"`

```

### 4. End-to-end testing (optional)

**First, detect the project type from PR files:**

| Indicator | Project Type |
|-----------|--------------|
| `*.xcodeproj`, `*.xcworkspace`, `Package.swift` (iOS) | iOS/macOS |
| `package.json`, `composer.json`, `src/views/*`, `*.html.*` | Web |
| Both iOS files AND web files | Hybrid (test both) |

After presenting the Summary Report, offer appropriate testing based on project type:

**For Web Projects:**
```markdown
**"Want to run browser tests on the affected pages?"**
1. Yes - run `/test-browser`
2. No - skip
```

**For Hybrid Projects:**
```markdown
**"Want to run end-to-end tests?"**
1. Web only - run `/test-browser`
2. Both web and native - run both commands
3. No - skip
```

#### If User Accepts Web Testing:

Spawn a subagent to run browser tests (preserves main context):

```
Task general-purpose("Run /test-browser for PR #[number]. Test all affected pages, check for console errors, handle failures by creating todos and fixing.")
```

The subagent will:
1. Identify pages affected by the PR
2. Navigate to each page and capture snapshots (using Playwright MCP or agent-browser CLI)
3. Check for console errors
4. Test critical interactions
5. Pause for human verification on OAuth/email/payment flows
6. Create P1 todos for any failures
7. Fix and retry until all tests pass

**Standalone:** `/test-browser [PR number]`

### Important: Critical Findings Block Merge

Any **Critical** findings must be addressed before merging the PR. Present these prominently and ensure they're resolved before accepting the PR.
```
