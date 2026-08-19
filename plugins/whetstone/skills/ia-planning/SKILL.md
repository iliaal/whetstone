---
name: ia-planning
class: workflow
description: >-
  Software implementation planning with file-based persistence (.plan/). Use
  when planning code changes touching 3+ files or with ambiguous scope. Skip
  for typos, single-file fixes, and research/scanning/audit work that
  produces reports rather than code.
---

# Planning

## Core Principle

```
Context window = RAM (volatile, limited)
Filesystem     = Disk (persistent, unlimited)
→ Anything important gets written to disk.
```

Planning tokens are cheaper than implementation tokens. Front-load thinking; scale effort to complexity.

## Procedure

1. Run the *Goal Quality Gate* on the stated goal.
2. Pick the path per *When to Plan*: full plan, flat list, or skip.
3. For a full plan, scaffold `.plan/` via [init-plan.sh](./scripts/init-plan.sh).
4. Write the plan per the *Plan Template*, applying the quality, sizing, and task rules.
5. Run the *Verify* checklist against the finished plan.
6. Offer the *Execution Handoff* choice.

## Goal Quality Gate

Run this gate before *When to Plan* below — a weak goal wastes tokens on any path and produces an unverifiable result. Answer these five questions first:

1. **What concrete thing will be true when this is done?** (named artifact, system state, or user-visible behavior — not "improve X" or "investigate Y")
2. **What evidence will prove it?** (specific test, command, screenshot, metric — not "looks right")
3. **What quantitative or binary threshold defines success?** (p95 < 250ms; `npm run test:checkout` passes; `gh pr view 123` shows no unresolved threads)
4. **What scope boundaries matter?** (which files/modules/environments are in scope; which are explicitly not)
5. **What should cause the agent to stop and ask?** (which decisions belong to the user, not Claude)

Then apply the Means test to the answer to question 1: **if the implementation changed, would this still be the goal?** If not, what was named is a Means, not the Objective. A request that supplies only an approach ("move the retry logic out of the controller into a job") passes all five questions while anchoring the plan to a mechanism -- and when the mechanism turns out wrong there is nothing left to re-derive the plan from. Recover the Objective from why the approach was proposed, keep the approach as the current best route, and record it as a decision rather than as the goal.

Reject pure-activity goals ("make progress", "keep investigating", "improve things") -- repair them into a verifiable outcome or ask one concise clarification before planning. Skip this gate only when the request already names a specific artifact AND a clear success signal in the user's own words -- the same choice-free cases listed under *When to Plan* below. Anything vaguer than that runs the gate.

## When to Plan

**Bias toward producing a plan.** A thin plan for small work is mild ceremony; skipping a plan when one was warranted costs real time (reinvented decisions, lost unit boundaries, no IDed requirements to verify against). When unsure, write the plan.

- **Full plan** (.plan/ directory): multi-file changes, new features, refactors, >5 tool calls
- **Flat list** (inline checklist): 3-5 file changes, clear scope, no research -- a numbered task list in the conversation or a single progress.md, no .plan/ scaffolding

**Skip planning only when ALL of these hold:** the work is **atomic** (one commit, no unit boundaries worth breaking out); there are **no KTDs** (Key Technical Decisions: choices between approaches; each KTD becomes a *Key Decisions* entry in the plan -- if one exists, plan); the **scope is self-evident** from the request, with no boundaries worth pinning in writing; and **no upstream artifact** (brainstorm, incident report, deferred follow-up) needs traceability through this plan.

**Stress test the "looks atomic" case.** Many requests look atomic but hide design decisions. *"Add caching to this endpoint"* sounds atomic, but TTL, invalidation, cache-key shape, and backend selection are all KTDs -- write the plan. The same trap hides in "migrate package A to B" and "add rate limiting". Genuine skips are choice-free: *"fix typo in README line 47"*, *"rename `oldFn` to `newFn` across the repo"*, *"bump lodash to 4.17.21"* (unless breaking changes warrant a unit-by-unit migration).

When skipping the plan doc, work proceeds directly to execution (`/ia-work` in Claude Code) or to implementation, and any decisions made along the way land in the commit message or `docs/solutions/` if worth carrying forward.

## Planning Files

Scaffold the `.plan/` directory with pre-populated templates using [init-plan.sh](./scripts/init-plan.sh):

```bash
SKILL_DIR="<absolute path of the directory containing this SKILL.md>"
bash "$SKILL_DIR/scripts/init-plan.sh" "Feature Name"
```

Substitute the real absolute path before running; never execute the command with the angle-bracket placeholder. Anchor the call to `SKILL_DIR` rather than a bare `init-plan.sh` — a relative path resolves against the caller's working directory, not the skill, and breaks from a subdirectory or under a non-Claude harness.

This creates `.plan/` with the three pre-populated files below and adds `.plan/` to `.gitignore`.

`.plan/` files are ephemeral working state -- do not commit them; old files are overwritten when starting a new feature. Within a multi-phase feature, use numbered intermediate files (`01-setup.md`, `02-phase1-complete.md`) to preserve state across phases. `docs/plans/` is the separate, committed home for a formal plan document; `.plan/` supports the work session.

| File | Purpose | Update When |
|------|---------|-------------|
| `.plan/task_plan.md` | Phases, tasks, decisions, errors | After each phase |
| `.plan/findings.md` | Research, discoveries, code analysis | After any discovery |
| `.plan/progress.md` | Session log, test results, files changed | Throughout session |

## Test Discovery (Existing Projects)

For existing code, discover the test landscape before planning: find related test/spec files (`Glob("**/*test*")`, `Grep`), read the canonical test command from config (`package.json` scripts, `pytest.ini`, `phpunit.xml`, CI), and note coverage gaps -- the plan should extend existing test patterns, not introduce new frameworks. Skip for greenfield projects with no tests yet.

## Reference Implementations

When target behavior is hard to describe but an existing implementation embodies it, cite that source as the spec and plan to reimplement its *semantics* -- source code is higher-fidelity than prose, docs, or screenshots. Record a `ref:` pointer in the plan so the implementer reads the source, not a summary. Full guidance in [execution-and-methodology.md](./references/execution-and-methodology.md).

## Plan Template

```markdown
# Plan: [Feature/Task Name]

## Approach
[1-3 sentences: what and why]

## Scope
- **In**: [what's included]
- **Out**: [what's explicitly excluded]

## Global Constraints
[Binds every phase: version floors; naming/format rules; platform limits; security/compatibility invariants. Exact spec values verbatim, never paraphrased. Every task inherits these. Omit if none.]

## Key Decisions (review first)
[Decisions likeliest to change on review: data model shapes; new type/interface contracts; user-facing or UX flows. Per decision: choice, discarded alternative, one-line why. Listed first so review redirects design before mechanical work is planned around it; mechanical refactoring stays in the phases. Omit if no non-obvious choice was made.]

## File Structure
[ALL files created or modified, one-line responsibility each; locks decomposition before tasks are defined. Write for a zero-context engineer.]

| File | Action | Responsibility |
|------|--------|---------------|
| `path/to/file.ts` | Create | [what this file does] |
| `path/to/existing.ts` | Modify | [what changes and why] |

## Next Step
[one line: the phase and task to resume on]

## Phase 1: [Name]
**Status**: pending | in_progress | complete
**Files**: [specific files, max 5-8 per phase]
**Posture**: [test-first | characterization-first | external-delegate]
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

**Keep phase state current.** Changing a phase's `Status` also refreshes `## Next Step`. That one line is what the resume protocol reads after a compaction or a new session, so a stale `Next Step` is worse than none -- it resumes work that already happened.

**No placeholders in tasks.** Every task must contain actual code patterns, commands, or file paths. Forbid: "TBD", "TODO", "handle errors appropriately", "add validation", "implement as needed", "similar to above", "Similar to Task N", "See above." Tasks may be read out of order -- repeat the spec, code pattern, or file path in every task that needs it. A step that cannot be specified concretely needs further breakdown before it belongs in a plan.

**Type-consistency check.** After writing all tasks, scan for naming drift. If Task 3 says `clearLayers()` but Task 7 says `clearFullLayers()`, that's a bug in the plan. Function names, variable names, and file paths must be consistent across all tasks.

**No gold-plating.** Build exactly what the spec requires -- no features or "nice-to-haves" beyond it. Quote the exact spec requirements in the plan and flag any additions explicitly as scope expansion needing approval. Basic first implementations are acceptable -- most need 2-3 revision cycles anyway.

**Front-load high-variance decisions.** Order the plan document by how likely each part is to change on review, not by execution order -- the template's *Key Decisions* bracket defines what goes there; execution order still governs the phases themselves.

## Phase Sizing Rules

Every phase must be **context-safe**:
- Max 5-8 files touched
- Max 2 dependencies on other phases
- No single task exceeds ~2 hours of focused work -- if it would, split further
- Fits in one focused session for a developer without external blockers
- If a phase violates these → split it
- **Scope challenge**: if the overall plan touches 8+ files or introduces 2+ new classes/services, challenge the scope. Ask: can this be split into smaller, independently shippable increments?

## Task Decomposition

Decompose by user-visible capability (vertical slices), not by technical layer, so each phase is independently demonstrable. Checkpoint every 2-3 tasks to catch integration drift early. Full guidance -- vertical slicing and the checkpoint system -- in [execution-and-methodology.md](./references/execution-and-methodology.md).

## Decision Authority

Not every decision needs user input:

**Claude decides (technical implementation):** language, framework, architecture, libraries, file structure, naming conventions, test strategy, error handling approach, database schema details, API design patterns. Make the call, document the rationale in the plan.

**User decides (experience-affecting):** scope tradeoffs ("cut X to hit deadline?"), UX choices that change what users see or do, data model decisions that constrain future product options, anything where two valid paths lead to meaningfully different user outcomes.

**Heuristic:** If the decision changes what the user *experiences*, ask. If it changes how the code *works*, decide.

## Clarifying Questions

Ask via AskUserQuestion (Claude Code; load with ToolSearch `select:AskUserQuestion` if not loaded) or request_user_input (Codex); fall back to numbered options in chat.

Scale to complexity:
- Small task: 0-1 questions, assume reasonable defaults
- Medium feature: 1-2 questions on critical unknowns
- Large project: 3-5 questions (auth, data model, integrations, scope)

Only ask about decisions that fall in the "user decides" category above. Make reasonable assumptions for everything else.

## Task Rules

Write every task as if the implementer has zero context and questionable taste -- they cannot infer intent from conversation history, so everything must be in the plan.

- **Atomic**: one action, 2-5 minutes to complete. "Write the failing test" is a step. "Implement the feature" is not.
- **Verb-first**: "Add...", "Create...", "Refactor...", "Verify..."
- **Concrete**: name specific files, endpoints, components. Include exact commands with expected output, code snippets, and file paths with line ranges for modifications.
- **Ordered**: respect dependencies, sequential when needed
- **Verifiable**: include at least one validation task per phase
- **Complete**: do not defer test coverage, skip edge cases, or omit error handling to save time. The marginal cost of completeness during initial implementation is near-zero compared to retrofitting later.

## Operational Patterns

Context management rules, error protocol (3-attempt escalation), iterative plan refinement, the 5-question context check, and session-continuity/traceability conventions (numbered outputs, resume protocol, SHA and deviation notes) are in [operational-patterns.md](./references/operational-patterns.md). Read when starting a multi-phase plan or resuming after a gap.

## Execution Posture Signals

Phases can carry optional metadata that shapes how `/ia-work` sequences implementation. Default is tests-after; opt in per phase via the header (`## Phase 2: Auth middleware [test-first]`): `test-first` (write failing test before implementation), `characterization-first` (capture existing behavior before changing it), `external-delegate` (mark units suitable for parallel/external execution). When to use each is in [execution-and-methodology.md](./references/execution-and-methodology.md).

## Plan Deepening

When asked to "deepen" or "strengthen" an existing plan, load [plan-deepening.md](./references/plan-deepening.md) — targeted research workflow (additive, not restructuring), per-section enhancement format, and Enhancement Summary block at the plan head. Orchestrated by the `/ia-deepen-plan` command.

## Execution Handoff

When a plan is complete, offer the user an explicit choice -- subagent-driven (dispatch each phase to a focused agent) or inline execution -- rather than drifting into implementation. State a one-sentence recommendation, then present the choice via the same ask mechanism as *Clarifying Questions* and wait for the user to pick; do not auto-start either path. Dispatch discipline and portable task-prompt anchoring are in [execution-and-methodology.md](./references/execution-and-methodology.md).

## Verify

- Plan file exists at `.plan/task_plan.md` (or `docs/plans/` for formal plans)
- All tasks are verb-first and atomic (2-5 minutes each)
- File structure table is complete with action and responsibility columns
- Phase sizing respects 5-8 file limit
- No placeholder tasks ("implement feature", "add tests") -- every task names specific files and patterns
- Each phase delivers end-to-end functionality (not a single horizontal layer)
- Open questions limited to 3 or fewer genuinely blocking unknowns

## Integration

- **Predecessor:** `ia-brainstorming` when requirements are ambiguous -- use an existing brainstorm spec (`docs/brainstorms/`) as input and skip idea refinement.
- **Architecture decisions:** record significant trade-offs (chosen approach, what was given up) as an ADR (`/ia-adr` in Claude Code); ADRs outlive the plan.
- **Threat modeling:** dispatch `ia-security-sentinel` in threat-model mode before implementation when the plan adds auth flows, payment handling, external API surfaces, or new trust boundaries -- architectural gaps are cheaper to fix in the plan than the code.
- **Prose quality:** `ia-writing` to humanize plan language and strip AI slop.
- **Execution handoff:** after approval, per *Execution Handoff* above.
