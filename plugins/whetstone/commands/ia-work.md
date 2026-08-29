---
name: ia-work
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

**Pipeline mode:** If invoked from an automated workflow (LFG or any `disable-model-invocation` context), skip all AskUserQuestion calls. Make decisions automatically: auto-proceed past the Phase 1 approval, resolve the branch-setup prompt by creating a new feature branch when on the default branch, and default the Phase 4 branch-finish choice to **Push + PR**. Never commit directly to the default branch, even in pipeline mode.

### Phase 1: Quick Start

1. **Read Plan and Clarify**

   - Read the work document completely
   - Review any references or links provided in the plan
   - If anything is unclear or ambiguous, ask clarifying questions now
   - Get user approval to proceed
   - **Do not skip this** - better to ask questions now than build the wrong thing
   - **Pipeline mode:** auto-proceed without waiting for approval (see Pipeline mode note above)

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

   Invoke the `ia-git-worktree` skill to create a new branch from the default branch in an isolated worktree.

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

   **System-Wide Test Check** -- Before marking a task done, run the blast-radius check from the `ia-verification-before-completion` skill's [system-wide-test-check.md](../skills/ia-verification-before-completion/references/system-wide-test-check.md). Skip for leaf-node changes with no callbacks or state persistence.

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

   - **Default ordering is tests-after** for new features: implement the smallest working version, then add tests alongside. The goal is that by the time the feature is done, tests exist and pass.
   - **Opt into tests-first** per phase by adding `[test-first]` to the phase header (see `ia-planning` skill, Execution Posture Signals). Use test-first when behavior is well-defined upfront (bug fixes always; new features when the contract is clear before implementation).
   - Run relevant tests after each significant change. Don't wait until the end.
   - Fix failures immediately.
   - **Unit tests with mocks prove logic in isolation. Integration tests with real objects prove the layers work together.** If your change touches callbacks, middleware, or error handling — you need both.

5. **Figma Design Sync** (if applicable)

   For UI work with Figma designs:

   - Implement components following design specs
   - Use `ia-figma-design-sync` agent iteratively to compare
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

7. **Subagent Execution Discipline**

   When dispatching subagents to implement tasks, follow the `ia-orchestrating-swarms` skill — it owns the full protocol: fresh-agent-per-task (no context reuse), two-stage review gate (spec compliance first, then quality), model-selection-by-complexity table, and the four-status reporting protocol (DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT). Do NOT restate those rules here. The skill is the source of truth — changes land there, not in this command.

### Phase 2.5: Verify Before Proceeding

Invoke the `ia-verification-before-completion` skill via an explicit Skill tool call and run its full gate (fresh evidence, positive executed-test count, binary identity, sweep completion). Do not proceed to Phase 3 if verification fails.

### Phase 3: Quality Check

1. **Run Core Quality Checks**

   Always run before submitting:

   ```bash
   # Run full test suite (use project's test command)
   # Examples: npm test, pytest, php artisan test, go test, etc.

   # Run linting (use project's lint command per CLAUDE.md)
   ```

2. **Code Review** (gate, not a judgement call)

   Read agents from `whetstone.local.md` frontmatter (`review_agents`). If no settings file, run `/ia-setup` to create one. Run configured agents in parallel with Task tool, present findings, and address critical issues.

   This step is not optional. It closes one of two ways, and both the PR template's Testing section and the Phase 4 Notify User summary have to say which:

   - **Reviewed** -- agents ran, findings presented, criticals addressed or explicitly accepted with a reason.
   - **Skipped**, with one of these stated verbatim plus a one-line reason: `Code review: skipped (mechanical diff)` for a rename, a formatting sweep, a lockfile bump, or a generated-file refresh where the diff carries no behavior change; `Code review: skipped (unavailable)` when no `review_agents` are configured and `/ia-setup` has not been run.

   A self-assessment does not close this gate. "I already reviewed it as I wrote it" and "the findings were applied during implementation" are the implementer judging their own work, which is what the review exists to avoid. If the diff is large enough to want a worktree and multiple lenses, hand it to `/ia-review` and record that as the receipt.

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
   PORT=$(bash ${CLAUDE_PLUGIN_ROOT}/commands/scripts/resolve-dev-port)
   agent-browser open "http://localhost:$PORT/[route]"
   agent-browser snapshot -i
   agent-browser screenshot output.png
   ```
   Resolve the port rather than assuming 3000 -- Vite and SvelteKit default to 5173, and `PORT=` in `.env` overrides either.
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

   Present options: **Merge locally** (solo work) / **Push + PR** (team work) / **Keep as-is** (WIP) / **Discard** (requires typed "discard" confirmation). In pipeline mode, skip the prompt and default to **Push + PR**.

   For PRs, use this template:
   ```
   ## Summary
   - [What was built and why]
   - [Key decisions made]

   ## Testing
   - [Tests added/modified]
   - [Manual testing performed]
   - `Code review: reviewed` (agents ran, findings addressed) — or one of the Phase 3 skip phrases verbatim: `Code review: skipped (mechanical diff)` / `Code review: skipped (unavailable)`, each followed by a one-line reason

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
   - State the Phase 3 code-review disposition verbatim (reviewed, or the skip phrase plus its reason)
   - Link to PR (if created)
   - Note any follow-up work needed
   - Suggest next steps if applicable

---

## Swarm Mode (Optional)

For swarm execution, follow the `ia-orchestrating-swarms` skill.

---

## Quality Checklist

Before creating PR, verify:

- [ ] All clarifying questions asked and answered
- [ ] All tasks marked completed (TaskList)
- [ ] Tests pass (run project's test command)
- [ ] Linting passes (run project's lint command)
- [ ] Code follows existing patterns
- [ ] Code review closed -- reviewed, or skipped with the verbatim phrase and reason from Phase 3
- [ ] Figma designs match implementation (if applicable)
- [ ] Before/after screenshots captured and uploaded (for UI changes)
- [ ] Commit messages follow conventional format
- [ ] PR description includes Post-Deploy Monitoring & Validation section (or explicit no-impact rationale)
- [ ] PR description includes summary, testing notes, and screenshots

## Integration

- **Predecessor:** `/ia-plan` (provides the plan to execute)
- **During execution:** `ia-verification-before-completion`, `ia-writing-tests`, `ia-debugging`
- **Next step:** Phase 4 Ship It (merge / PR / keep / discard)
