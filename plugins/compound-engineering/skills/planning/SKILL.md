---
name: planning
description: >-
  Software implementation planning with file-based persistence (.plan/). Use when
  asked to plan, break down a feature, or starting complex tasks. Apply
  proactively before non-trivial coding.
---

# Planning

## Core Principle

```
Context window = RAM (volatile, limited)
Filesystem     = Disk (persistent, unlimited)
→ Anything important gets written to disk.
```

Planning tokens are cheaper than implementation tokens. Front-load thinking; scale effort to complexity.

## When to Plan

- **Full plan** (.plan/ directory): multi-file changes, new features, refactors, >5 tool calls
- **Flat list** (inline checklist): 3-5 file changes, clear scope, no research needed -- write a numbered task list in the conversation or a single progress.md, skip .plan/ scaffolding
- **Skip planning**: single-file edits, quick lookups, simple questions

## Planning Files

Scaffold the `.plan/` directory with pre-populated templates using [init-plan.sh](./scripts/init-plan.sh):

```bash
bash init-plan.sh "Feature Name"
```

This creates `.plan/` with `task_plan.md`, `findings.md`, and `progress.md` -- each pre-populated with the correct structure. Also adds `.plan/` to `.gitignore`.

Planning files are ephemeral working state -- do not commit them. If working on multiple features sequentially, old files are overwritten; the plan captures the current task only.

**Note:** `.plan/` is for ephemeral working state during implementation (scratch notes, progress tracking). `docs/plans/` is for the formal plan document created by `workflows:plan` (committed, living documents). Both coexist -- `.plan/` supports the work session, `docs/plans/` stores the committed plan.

| File | Purpose | Update When |
|------|---------|-------------|
| `.plan/task_plan.md` | Phases, tasks, decisions, errors | After each phase |
| `.plan/findings.md` | Research, discoveries, code analysis | After any discovery |
| `.plan/progress.md` | Session log, test results, files changed | Throughout session |

## Plan Template

```markdown
# Plan: [Feature/Task Name]

## Approach
[1-3 sentences: what and why]

## Scope
- **In**: [what's included]
- **Out**: [what's explicitly excluded]

## File Structure
[Map ALL files that will be created or modified, with one-line responsibility for each. Lock in decomposition decisions before defining tasks. Write for a zero-context engineer.]

| File | Action | Responsibility |
|------|--------|---------------|
| `path/to/file.ts` | Create | [what this file does] |
| `path/to/existing.ts` | Modify | [what changes and why] |

## Phase 1: [Name]
**Files**: [specific files, max 5-8 per phase]
**Tasks**:
- [ ] [Verb-first atomic task] -- `path/to/file.ts`
- [ ] [Next task]
**Verify**: [specific test: "POST /api/users → 201", not "test feature"]
**Exit**: [clear done definition]

## Phase 2: [Name]
...

## Deferred to Implementation
- [Things intentionally left unspecified -- details that depend on what you find in the code]

## Open Questions
- [Max 3, only truly blocking unknowns]
```

### Plan Quality Rules

**No placeholders between tasks.** Each task must be self-contained. Never write "Similar to Task N" or "See above" -- repeat the spec, code pattern, or file path in every task that needs it. The implementer may read tasks out of order.

**Type-consistency check.** After writing all tasks, scan for naming drift. If Task 3 says `clearLayers()` but Task 7 says `clearFullLayers()`, that's a bug in the plan. Function names, variable names, and file paths must be consistent across all tasks.

**Numbered outputs for long sessions.** For multi-phase implementations, write numbered intermediate files to `.plan/` (e.g., `01-setup.md`, `02-phase1-complete.md`) so state survives context compaction. Read from files, not conversation memory, when resuming work after compaction or across sessions.

**SHA recording.** When a task completes and is committed, note the commit SHA inline: `- [x] Task 1.1 \`abc1234\``. Creates traceability from plan to code.

**Deviation documentation.** When the implementation deviates from the plan, document why inline: `**Deviation**: [what changed and why]` under the affected task. Silent deviation breaks trust -- the orchestrator assumes the plan was followed.

**No gold-plating.** Build exactly what the spec requires. If a feature, enhancement, or "nice-to-have" isn't in the requirements, don't add it. Quote the exact spec requirements in the plan and flag any additions explicitly as scope expansion needing approval. Basic first implementations are acceptable -- most need 2-3 revision cycles anyway.

## Phase Sizing Rules

Every phase must be **context-safe**:
- Max 5-8 files touched
- Max 2 dependencies on other phases
- Fits in one focused session for a developer without external blockers
- If a phase violates these → split it
- **Scope challenge**: if the overall plan touches 8+ files or introduces 2+ new classes/services, challenge the scope. Ask: can this be split into smaller, independently shippable increments?

## Decision Authority

Not every decision needs user input. Apply this principle:

**Claude decides (technical implementation):** language, framework, architecture, libraries, file structure, naming conventions, test strategy, error handling approach, database schema details, API design patterns. Make the call, document the rationale in the plan.

**User decides (experience-affecting):** scope tradeoffs ("cut X to hit deadline?"), UX choices that change what users see or do, data model decisions that constrain future product options, anything where two valid paths lead to meaningfully different user outcomes.

**Heuristic:** If the decision changes what the user *experiences*, ask. If it changes how the code *works*, decide.

## Clarifying Questions

Scale to complexity:
- Small task: 0-1 questions, assume reasonable defaults
- Medium feature: 1-2 questions on critical unknowns
- Large project: 3-5 questions (auth, data model, integrations, scope)

Only ask about decisions that fall in the "user decides" category above. Make reasonable assumptions for everything else.

## Task Rules

Write every task as if the implementer has zero context and questionable taste. They cannot infer intent from conversation history -- everything must be in the plan.

- **Atomic**: one action, 2-5 minutes to complete. "Write the failing test" is a step. "Implement the feature" is not.
- **Verb-first**: "Add...", "Create...", "Refactor...", "Verify..."
- **Concrete**: name specific files, endpoints, components. Include exact commands with expected output, code snippets (not "add validation"), and file paths with line ranges for modifications.
- **Ordered**: respect dependencies, sequential when needed
- **Verifiable**: include at least one validation task per phase
- **Complete**: do not defer test coverage, skip edge cases, or omit error handling to save time. The marginal cost of completeness during initial implementation is near-zero compared to retrofitting later.

## Context Management Rules

| Situation | Action |
|-----------|--------|
| Starting new phase | Read .plan/task_plan.md (refresh goals in attention window) |
| After any discovery | Write to .plan/findings.md immediately |
| After completing phase | Update .plan/task_plan.md status, log to .plan/progress.md |
| After viewing image/PDF | Write findings NOW (multimodal content doesn't persist) |
| Resuming after gap | Read all planning files, run `git diff --stat` to reconcile actual vs planned state |
| Just wrote a file | Don't re-read it (still in context) |
| Error occurred | Log to .plan/task_plan.md, read relevant files for state |

## Error Protocol

```
ATTEMPT 1: Diagnose root cause → targeted fix
ATTEMPT 2: Different approach (different tool, library, method)
ATTEMPT 3: Question assumptions → search for solutions → update plan
AFTER 3 FAILURES: Escalate to user with what you tried
```

**Never repeat the exact same failing action.** Track attempts, mutate approach.

## Iterative Refinement

For complex projects, iterate on the plan before implementing:
1. Draft initial plan
2. Dispatch a plan-reviewer subagent with the plan document and original spec (not session history) to evaluate completeness, feasibility, and gaps
3. Fix issues found, re-dispatch reviewer if needed (max 3 iterations)
4. Present to user for final approval before implementation

## 5-Question Context Check

If you can answer these, your planning is solid:

| Question | Source |
|----------|--------|
| Where am I? | Current phase in .plan/task_plan.md |
| Where am I going? | Remaining phases |
| What's the goal? | Approach section |
| What have I learned? | .plan/findings.md |
| What have I done? | .plan/progress.md |

## Anti-Patterns

| Don't | Do Instead |
|-------|------------|
| Start coding without a plan | Create .plan/task_plan.md first |
| State goals once and forget | Re-read plan before decisions |
| Hide errors and retry silently | Log errors, mutate approach |
| Keep everything in context | Write large content to files |
| Repeat failed actions | Track attempts in plan file |
| Create vague tasks ("improve X") | Concrete verb-first tasks with file paths |
| Plan phases with 12+ files | Split into 5-8 file chunks |
| Plan at 100% capacity | Budget for verification, fixes, and unknowns |

## Integration

- **This skill** is methodology (file persistence, phase sizing, context management). `workflows:plan` is the structured workflow (research agents, issue templates). Use this skill's principles during any planning; use `workflows:plan` for full feature plans.
- **Architecture decisions:** when the plan involves significant trade-offs (choosing between approaches, accepting constraints), use `/adr` to document the decision and what was given up. ADRs outlive the plan.
- **Predecessor:** `brainstorming` -- use first when requirements are ambiguous. When a brainstorm spec exists (`docs/brainstorms/`), use it as input and skip idea refinement
- **Prose quality:** `writing` -- use to humanize plan language and remove AI slop from plan documents
- **Execution handoff:** after the plan is approved, proceed to `workflows:work` or execute inline
