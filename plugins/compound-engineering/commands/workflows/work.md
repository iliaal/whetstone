---
name: workflows:work
description: Execute work plans efficiently while maintaining quality and finishing features
argument-hint: "[plan file, specification, or todo file path]"
---

# Work Plan Execution Command

Execute a work plan efficiently while maintaining quality and finishing features.

## Introduction

This command takes a work document (plan, specification, or todo file) and executes it systematically. The focus is on **shipping complete features** by understanding requirements quickly, following existing patterns, and maintaining quality throughout.

## Input Document

**Input document:** #$ARGUMENTS

## Execution Workflow

### Phase 1: Quick Start

1. **Read Plan and Clarify**

   - Read the work document completely
   - Review any references or links provided in the plan
   - If anything is unclear or ambiguous, ask clarifying questions now
   - Get user approval to proceed
   - **Do not skip this** - better to ask questions now than build the wrong thing

2. **Setup Environment**

   First, check the current branch:

   ```bash
   current_branch=$(git branch --show-current)
   default_branch=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')

   # Fallback if remote HEAD isn't set
   if [ -z "$default_branch" ]; then
     default_branch=$(git rev-parse --verify origin/main >/dev/null 2>&1 && echo "main" || echo "master")
   fi
   ```

   **If already on a feature branch** (not the default branch):
   - Ask: "Continue working on `[current_branch]`, or create a new branch?"
   - If continuing, proceed to step 3
   - If creating new, follow Option A or B below

   **If on the default branch**, choose how to proceed:

   **Option A: Create a new branch**
   ```bash
   git pull origin [default_branch]
   git checkout -b feature-branch-name
   ```
   Use a meaningful name based on the work (e.g., `feat/user-authentication`, `fix/email-validation`).

   **Option B: Use a worktree (recommended for parallel development)**
   ```bash
   skill: git-worktree
   # The skill will create a new branch from the default branch in an isolated worktree
   ```

   **Option C: Continue on the default branch**
   - Requires explicit user confirmation
   - Only proceed after user explicitly says "yes, commit to [default_branch]"
   - Never commit directly to the default branch without explicit permission

   **Recommendation**: Use worktree if:
   - You want to work on multiple features simultaneously
   - You want to keep the default branch clean while experimenting
   - You plan to switch between branches frequently

3. **Create Todo List**
   - Use TaskCreate to break plan into actionable tasks
   - Include dependencies between tasks
   - Prioritize based on what needs to be done first
   - Include testing and quality check tasks
   - Keep tasks specific and completable

### Phase 2: Execute

1. **Task Execution Loop**

   For each task in priority order:

   ```
   while (tasks remain):
     - Mark task as in_progress via TaskUpdate
     - Read any referenced files from the plan
     - Look for similar patterns in codebase
     - Implement following existing conventions
     - Write tests for new functionality
     - Run System-Wide Test Check (see below)
     - Run tests after changes
     - Mark task as completed via TaskUpdate
     - Mark off the corresponding checkbox in the plan file ([ ] → [x])
     - Evaluate for incremental commit (see below)
   ```

   **System-Wide Test Check** -- Before marking a task done, run the blast-radius check from the `verification-before-completion` skill's [system-wide-test-check.md](../../skills/verification-before-completion/references/system-wide-test-check.md). Skip for leaf-node changes with no callbacks or state persistence.

   **IMPORTANT**: Always update the original plan document by checking off completed items. Use the Edit tool to change `- [ ]` to `- [x]` for each task you finish. This keeps the plan as a living document showing progress and ensures no checkboxes are left unchecked.

2. **Incremental Commits**

   After completing each task, evaluate whether to create an incremental commit:

   | Commit when... | Don't commit when... |
   |----------------|---------------------|
   | Logical unit complete (model, service, component) | Small part of a larger unit |
   | Tests pass + meaningful progress | Tests failing |
   | About to switch contexts (backend → frontend) | Purely scaffolding with no behavior |
   | About to attempt risky/uncertain changes | Would need a "WIP" commit message |

   **Heuristic:** "Can I write a commit message that describes a complete, valuable change? If yes, commit. If the message would be 'WIP' or 'partial X', wait."

   **Commit workflow:**
   ```bash
   # 1. Verify tests pass (use project's test command)
   # Examples: npm test, pytest, php artisan test, go test, etc.

   # 2. Stage only files related to this logical unit (not `git add .`)
   git add <files related to this logical unit>

   # 3. Commit with conventional message
   git commit -m "feat(scope): description of this unit"
   ```

   **Handling merge conflicts:** If conflicts arise during rebasing or merging, resolve them immediately. Incremental commits make conflict resolution easier since each commit is small and focused.

   **Note:** Incremental commits use clean conventional messages without attribution footers.

3. **Follow Existing Patterns**

   - The plan should reference similar code - read those files first
   - Match naming conventions exactly
   - Reuse existing components where possible
   - Follow project coding standards (see CLAUDE.md)
   - When in doubt, grep for similar implementations

4. **Test Continuously**

   - Run relevant tests after each significant change
   - Don't wait until the end to test
   - Fix failures immediately
   - Add new tests for new functionality
   - **Unit tests with mocks prove logic in isolation. Integration tests with real objects prove the layers work together.** If your change touches callbacks, middleware, or error handling -- you need both.

5. **Figma Design Sync** (if applicable)

   For UI work with Figma designs:

   - Implement components following design specs
   - Use figma-design-sync agent iteratively to compare
   - Fix visual differences identified
   - Repeat until implementation matches design

6. **Track Progress**
   - Keep task list updated (TaskUpdate) as you complete tasks
   - Note any blockers or unexpected discoveries
   - Create new tasks if scope expands
   - Keep user informed of major milestones using **experiential framing**:
     - Lead with what changed from the user's perspective, then the technical detail
     - "Users can now reset their password via email (added PasswordResetController + mailer)"
     - "Search results load instantly on repeat queries (added Redis caching layer)"
     - Not: "Added PasswordResetController, ResetMailer, and migration for password_reset_tokens"

### Phase 2.5: Verify Before Proceeding

Before moving to quality checks, run the `verification-before-completion` gate:

1. Identify the verification command (project's test suite)
2. Run it fresh -- not "it passed earlier"
3. Read the full output -- check exit code, failure counts
4. Confirm all tasks are actually complete (check TaskList)

Do not proceed to Phase 3 if verification fails.

### Phase 3: Quality Check

1. **Run Core Quality Checks**

   Always run before submitting:

   ```bash
   # Run full test suite (use project's test command)
   # Examples: npm test, pytest, php artisan test, go test, etc.

   # Run linting (use project's lint command per CLAUDE.md)
   ```

2. **Consider Reviewer Agents** (Optional)

   Use for complex, risky, or large changes. Read agents from `compound-engineering.local.md` frontmatter (`review_agents`). If no settings file, run `/setup` to create one.

   Run configured agents in parallel with Task tool. Present findings and address critical issues.

3. **Final Validation**
   - All tasks marked completed (TaskList)
   - All tests pass
   - Linting passes
   - Code follows existing patterns
   - Figma designs match (if applicable)
   - No console errors or warnings

4. **Prepare Operational Validation Plan** (REQUIRED)
   - Add a `## Post-Deploy Monitoring & Validation` section to the PR description for every change.
   - Include concrete:
     - Log queries/search terms
     - Metrics or dashboards to watch
     - Expected healthy signals
     - Failure signals and rollback/mitigation trigger
     - Validation window and owner
   - If there is truly no production/runtime impact, still include the section with: `No additional operational monitoring required` and a one-line reason.

### Phase 4: Ship It

1. **Capture and Upload Screenshots for UI Changes** (REQUIRED for any UI work)

   For **any** design changes, new views, or UI modifications, you MUST capture and upload screenshots:

   **Step 1: Start dev server** (if not running)
   ```bash
   npm run dev  # Run in background
   ```

   **Step 2: Capture screenshots with agent-browser CLI**
   ```bash
   agent-browser open http://localhost:3000/[route]
   agent-browser snapshot -i
   agent-browser screenshot output.png
   ```
   Run `agent-browser --help` for full CLI usage.

   **Step 3: Upload screenshots**
   ```bash
   # Upload using imgup CLI (if available):
   imgup -h pixhost screenshot.png  # pixhost works without API key
   # Alternative hosts: catbox, imagebin, beeimg
   ```

   **What to capture:**
   - **New screens**: Screenshot of the new UI
   - **Modified screens**: Before AND after screenshots
   - **Design implementation**: Screenshot showing Figma design match

   **IMPORTANT**: Always include uploaded image URLs in PR description. This provides visual context for reviewers and documents the change.

2. **Update Plan Status**

   If the input document has YAML frontmatter with a `status` field, update it to `completed`:
   ```
   status: active  →  status: completed
   ```

3. **Finish the Branch**

   Present options: **Merge locally** (solo work) / **Push + PR** (team work) / **Keep as-is** (WIP) / **Discard** (requires typed "discard" confirmation).

   For PRs, use this template:
   ```
   ## Summary
   - [What was built and why]
   - [Key decisions made]

   ## Testing
   - [Tests added/modified]
   - [Manual testing performed]

   ## Post-Deploy Monitoring & Validation
   - **What to monitor**: [logs, metrics, dashboards]
   - **Expected healthy behavior**: [signals]
   - **Failure signals / rollback trigger**: [trigger + action]
   - **If no operational impact**: `No additional monitoring required: <reason>`

   ## Before / After Screenshots
   | Before | After |
   |--------|-------|
   | ![before](URL) | ![after](URL) |
   ```

   **Safety rules:**
   - Never proceed with failing tests
   - Never force-push without explicit user request
   - Never merge directly to main/master without explicit user permission
   - Always run tests after merge. If tests fail: revert (`git revert -m 1 HEAD`), keep branch, diagnose

4. **Notify User**
   - Summarize what was completed using experiential framing (what the user/end-user can now do, then technical details)
   - Link to PR (if created)
   - Note any follow-up work needed
   - Suggest next steps if applicable

---

## Swarm Mode (Optional)

For swarm execution, follow the `orchestrating-swarms` skill.

---

## Quality Checklist

Before creating PR, verify:

- [ ] All clarifying questions asked and answered
- [ ] All tasks marked completed (TaskList)
- [ ] Tests pass (run project's test command)
- [ ] Linting passes (run project's lint command)
- [ ] Code follows existing patterns
- [ ] Figma designs match implementation (if applicable)
- [ ] Before/after screenshots captured and uploaded (for UI changes)
- [ ] Commit messages follow conventional format
- [ ] PR description includes Post-Deploy Monitoring & Validation section (or explicit no-impact rationale)
- [ ] PR description includes summary, testing notes, and screenshots

## Integration

- **Predecessor:** `workflows:plan` (provides the plan to execute)
- **During execution:** `verification-before-completion`, `writing-tests`, `debugging`
- **Next step:** Phase 4 Ship It (merge / PR / keep / discard)
