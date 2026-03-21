---
name: workflows:review
description: Perform exhaustive code reviews using multi-agent analysis, ultra-thinking, and worktrees
argument-hint: "[PR number, GitHub URL, branch name, or latest]"
---

# Review Command

<command_purpose> Perform exhaustive code reviews using multi-agent analysis, ultra-thinking, and Git worktrees for deep local inspection. </command_purpose>

## Introduction

<role>Senior Code Review Architect with expertise in security, performance, architecture, and quality assurance</role>

## Prerequisites

<requirements>
- Git repository with GitHub CLI (`gh`) installed and authenticated
- Clean main/master branch
- Proper permissions to create worktrees and access the repository
- For document reviews: Path to a markdown file or document
</requirements>

## Main Tasks

### 1. Determine Review Target & Setup (ALWAYS FIRST)

<review_target> #$ARGUMENTS </review_target>

<thinking>
First, I need to determine the review target type and set up the code for analysis.
</thinking>

#### Immediate Actions:

<task_list>

- [ ] Determine review type: PR number (numeric), GitHub URL, file path (.md), or empty (current branch)
- [ ] Check current git branch
- [ ] If ALREADY on the target branch (PR branch, requested branch name, or the branch already checked out for review) → proceed with analysis on current branch
- [ ] If DIFFERENT branch than the review target → offer to use worktree: "Use git-worktree skill for isolated Call `skill: git-worktree` with branch name
- [ ] Fetch PR metadata using `gh pr view --json` for title, body, files, linked issues
- [ ] Set up language-specific analysis tools
- [ ] Prepare security scanning environment
- [ ] Make sure we are on the branch we are reviewing. Use gh pr checkout to switch to the branch or manually checkout the branch.

Ensure that the code is ready for analysis (either in worktree or on current branch). ONLY then proceed to the next step.

</task_list>

#### Protected Artifacts

<protected_artifacts>
The following paths are compound-engineering pipeline artifacts and must never be flagged for deletion, removal, or gitignore by any review agent:

- `docs/plans/*.md` — Plan files created by `/workflows:plan`. These are living documents that track implementation progress (checkboxes are checked off by `/workflows:work`).
- `docs/solutions/*.md` — Solution documents created during the pipeline.

If a review agent flags any file in these directories for cleanup or removal, discard that finding during synthesis. Do not create a todo for it.
</protected_artifacts>

#### Load Review Agents

Read `compound-engineering.local.md` in the project root. If found, use `review_agents` from YAML frontmatter. If the markdown body contains review context, pass it to each agent as additional instructions.

If no settings file exists, run `/setup` to create one. Then read the newly created file and continue.

#### Parallel Agents to review the PR:

<parallel_tasks>

Run all configured review agents in parallel using Task tool. For each agent in the `review_agents` list:

```
Task {agent-name}(PR content + review context from settings body)
```

Additionally, always run these regardless of settings:
- Task agent-native-reviewer(PR content) - Verify new features are agent-accessible
- Task learnings-researcher(PR content) - Search docs/solutions/ for past issues related to this PR's modules and patterns

</parallel_tasks>

#### Conditional Agents (Run if applicable):

<conditional_agents>

These agents are run ONLY when the PR matches specific criteria. Check the PR files list to determine if they apply:

**MIGRATIONS: If PR contains database migrations, schema.rb, or data backfills:**

- Task data-migration-expert(PR content) - Validates ID mappings match production, checks for swapped values, verifies rollback safety
- Task deployment-verification-agent(PR content) - Creates Go/No-Go deployment checklist with SQL verification queries

**When to run:**
- PR includes files matching `db/migrate/*.rb` or `db/schema.rb`
- PR modifies columns that store IDs, enums, or mappings
- PR includes data backfill scripts or rake tasks
- PR title/body mentions: migration, backfill, data transformation, ID mapping

**What these agents check:**
- `data-migration-expert`: Verifies hard-coded mappings match production reality (prevents swapped IDs), checks for orphaned associations, validates dual-write patterns
- `deployment-verification-agent`: Produces executable pre/post-deploy checklists with SQL queries, rollback procedures, and monitoring plans

</conditional_agents>

### 2. Ultra-Thinking Deep Dive Phases

<ultrathink_instruction> For each phase below, spend maximum cognitive effort. Think step by step. Consider all angles. Question assumptions. And bring all reviews in a synthesis to the user.</ultrathink_instruction>

<deliverable>
Complete system context map with component interactions
</deliverable>

#### Phase 3: Stakeholder Perspective Analysis

<thinking_prompt> ULTRA-THINK: Put yourself in each stakeholder's shoes. What matters to them? What are their pain points? </thinking_prompt>

<stakeholder_perspectives>

1. **Developer Perspective** <questions>

   - How easy is this to understand and modify?
   - Are the APIs intuitive?
   - Is debugging straightforward?
   - Can I test this easily? </questions>

2. **Operations Perspective** <questions>

   - How do I deploy this safely?
   - What metrics and logs are available?
   - How do I troubleshoot issues?
   - What are the resource requirements? </questions>

3. **End User Perspective** <questions>

   - Is the feature intuitive?
   - Are error messages helpful?
   - Is performance acceptable?
   - Does it solve my problem? </questions>

4. **Security Team Perspective** <questions>

   - What's the attack surface?
   - Are there compliance requirements?
   - How is data protected?
   - What are the audit capabilities? </questions>

5. **Business Perspective** <questions>
   - What's the ROI?
   - Are there legal/compliance risks?
   - How does this affect time-to-market?
   - What's the total cost of ownership? </questions> </stakeholder_perspectives>

#### Phase 4: Scenario Exploration

<thinking_prompt> ULTRA-THINK: Explore edge cases and failure scenarios. What could go wrong? How does the system behave under stress? </thinking_prompt>

<scenario_checklist>

- [ ] **Happy Path**: Normal operation with valid inputs
- [ ] **Invalid Inputs**: Null, empty, malformed data
- [ ] **Boundary Conditions**: Min/max values, empty collections
- [ ] **Concurrent Access**: Race conditions, deadlocks
- [ ] **Scale Testing**: 10x, 100x, 1000x normal load
- [ ] **Network Issues**: Timeouts, partial failures
- [ ] **Resource Exhaustion**: Memory, disk, connections
- [ ] **Security Attacks**: Injection, overflow, DoS
- [ ] **Data Corruption**: Partial writes, inconsistency
- [ ] **Cascading Failures**: Downstream service issues </scenario_checklist>

### 3. Multi-Angle Review Perspectives

#### Technical Excellence Angle

- Code craftsmanship evaluation
- Engineering best practices
- Technical documentation quality
- Tooling and automation assessment

#### Business Value Angle

- Feature completeness validation
- Performance impact on users
- Cost-benefit analysis
- Time-to-market considerations

#### Risk Management Angle

- Security risk assessment
- Operational risk evaluation
- Compliance risk verification
- Technical debt accumulation

#### Team Dynamics Angle

- Code review etiquette
- Knowledge sharing effectiveness
- Collaboration patterns
- Mentoring opportunities

### 4. Simplification and minimalism review

Run the Task code-simplicity-reviewer() to see if we can simplify the code. Note: `code-simplicity-reviewer` always runs here — exclude it from `review_agents` in `compound-engineering.local.md` to avoid running it twice.

### 5. Findings synthesis and todo creation

<critical_requirement> ALL findings MUST be stored in the todos/ directory using the file-todos skill. Create todo files immediately after synthesis - do NOT present findings for user approval first. Use the skill for structured todo management. </critical_requirement>

#### Step 1: Synthesize All Findings

<thinking>
Consolidate all agent reports into a categorized list of findings.
Remove duplicates, prioritize by severity and impact.
</thinking>

<synthesis_tasks>

- [ ] Collect findings from all parallel agents
- [ ] Surface learnings-researcher results: if past solutions are relevant, flag them as "Known Pattern" with links to docs/solutions/ files
- [ ] Discard any findings that recommend deleting or gitignoring files in `docs/plans/` or `docs/solutions/` (see Protected Artifacts above)
- [ ] Categorize by type: security, performance, architecture, quality, etc.
- [ ] Assign severity levels: 🔴 CRITICAL (P1), 🟡 IMPORTANT (P2), 🔵 NICE-TO-HAVE (P3)
- [ ] Remove duplicate or overlapping findings
- [ ] Estimate effort for each finding (Small/Medium/Large)

</synthesis_tasks>

#### Step 2: Create Todo Files

Create todo files for ALL findings immediately using the `file-todos` skill. Do not present findings one-by-one for user approval — create all todos, then summarize.

For large PRs (15+ findings), launch parallel sub-agents grouped by severity (one per P1/P2/P3 batch). Always add `code-review` tag plus relevant domain tags (`security`, `performance`, `architecture`, etc.).

#### Step 3: Summary Report

After creating all todo files, present comprehensive summary:

````markdown
## ✅ Code Review Complete

**Review Target:** PR #XXXX - [PR Title] **Branch:** [branch-name]

### Findings Summary:

- **Total Findings:** [X]
- **🔴 CRITICAL (P1):** [count] - BLOCKS MERGE
- **🟡 IMPORTANT (P2):** [count] - Should Fix
- **🔵 NICE-TO-HAVE (P3):** [count] - Enhancements

### Created Todo Files:

**P1 - Critical (BLOCKS MERGE):**

- `001-pending-p1-{finding}.md` - {description}
- `002-pending-p1-{finding}.md` - {description}

**P2 - Important:**

- `003-pending-p2-{finding}.md` - {description}
- `004-pending-p2-{finding}.md` - {description}

**P3 - Nice-to-Have:**

- `005-pending-p3-{finding}.md` - {description}

### Review Agents Used:

- security-sentinel
- performance-oracle
- architecture-strategist
- agent-native-reviewer
- [other agents]

### Next Steps:

1. **Address P1 Findings**: CRITICAL - must be fixed before merge

   - Review each P1 todo in detail
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
   /resolve_todo_parallel  # Fix all approved items efficiently
   ```

4. **Track Progress**:
   - Rename file when status changes: pending → ready → complete
   - Update Work Log as you work
   - Commit todos: `git add todos/ && git commit -m "refactor: add code review findings"`

```

### 6. End-to-end testing (optional)

<detect_project_type>

**First, detect the project type from PR files:**

| Indicator | Project Type |
|-----------|--------------|
| `*.xcodeproj`, `*.xcworkspace`, `Package.swift` (iOS) | iOS/macOS |
| `Gemfile`, `package.json`, `app/views/*`, `*.html.*` | Web |
| Both iOS files AND web files | Hybrid (test both) |

</detect_project_type>

<offer_testing>

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

</offer_testing>

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

### Important: P1 Findings Block Merge

Any **🔴 P1 (CRITICAL)** findings must be addressed before merging the PR. Present these prominently and ensure they're resolved before accepting the PR.
```
