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

## Test Discovery (Existing Projects)

For projects with existing code (not greenfield), discover the test landscape before planning:

1. Search for test/spec files related to the feature area: `Glob("**/*test*")` and `Grep("<feature-keyword>", glob="**/*.{ts,php,py}")`
2. Check test config for the canonical test command (`package.json` scripts, `pytest.ini`, `phpunit.xml`, CI config)
3. Note which modules have coverage and which don't -- plan should extend existing test patterns, not introduce new frameworks

Skip for greenfield projects where no tests exist yet.

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

## Execution Posture
- [Optional per-phase signals that shape implementation sequencing]
  - `test-first`: write failing test before implementation
  - `characterization-first`: capture existing behavior before changing it
  - `external-delegate`: mark units suitable for parallel/external execution

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

## Operational Patterns

Context management rules, error protocol (3-attempt escalation), iterative plan refinement, and the 5-question context check are in [operational-patterns.md](./references/operational-patterns.md). Read when starting a multi-phase plan or resuming after a gap.

## Execution Posture Signals

Plans can carry lightweight metadata per phase that shapes how `workflows:work` sequences implementation. These are optional annotations, not requirements.

- **test-first**: Write failing tests before implementation. Use when behavior is well-defined and testable upfront.
- **characterization-first**: Capture existing behavior with tests before changing it. Use when modifying code without existing test coverage.
- **external-delegate**: Mark self-contained units suitable for parallel execution (separate worktree, separate agent). Use when a phase has no dependencies on other phases.

Add posture signals in the phase header: `## Phase 2: Auth middleware [test-first]`. The executor inherits these silently without interrupting questions -- they shape sequencing, not scope.

## Plan Deepening

When asked to "deepen" or "strengthen" an existing plan, don't re-run the full planning workflow. Instead:

1. Read the existing plan file
2. Identify phases or tasks that are vague, under-specified, or missing verification steps
3. For each weak area, run targeted research (read relevant code, check existing patterns, verify assumptions)
4. Expand the weak sections with concrete file paths, code patterns, and verification steps
5. Preserve everything that's already specific enough

Deepening is additive -- it fills gaps without restructuring what already works. The `/deepen-plan` command orchestrates this with parallel research agents per section.

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

## Verify

- Plan file exists at `.plan/task_plan.md` (or `docs/plans/` for formal plans)
- All tasks are verb-first and atomic (2-5 minutes each)
- File structure table is complete with action and responsibility columns
- Phase sizing respects 5-8 file limit
- No placeholder tasks ("implement feature", "add tests") -- every task names specific files and patterns
- Open questions limited to 3 or fewer genuinely blocking unknowns

## Integration

- **This skill** is methodology (file persistence, phase sizing, context management). `workflows:plan` is the structured workflow (research agents, issue templates). Use this skill's principles during any planning; use `workflows:plan` for full feature plans.
- **Architecture decisions:** when the plan involves significant trade-offs (choosing between approaches, accepting constraints), use `/adr` to document the decision and what was given up. ADRs outlive the plan.
- **Predecessor:** `brainstorming` -- use first when requirements are ambiguous. When a brainstorm spec exists (`docs/brainstorms/`), use it as input and skip idea refinement
- **Prose quality:** `writing` -- use to humanize plan language and remove AI slop from plan documents
- **Execution handoff:** after the plan is approved, proceed to `workflows:work` or execute inline
