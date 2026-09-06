---
name: ia-planning
class: workflow
description: >-
  Software implementation planning with optional file-based persistence. Use
  when asked to plan, when unresolved architecture or scope decisions need a
  durable record, or when multi-phase implementation needs recovery state.
  For the full research-and-issue workflow, use the ia-plan command (/ia-plan
  in Claude Code).
---

# Planning

## Core Principle

```
Context window = RAM (volatile, limited)
Filesystem     = Disk (persistent, unlimited)
→ Persist only state that would be costly to reconstruct.
```

Planning exists to reduce implementation risk and preserve necessary state. Scale it to unresolved decisions, dependency depth, and continuity needs rather than file count or tool activity alone.

## Procedure

1. Run the *Goal Quality Gate* on the stated goal.
2. Pick the path per *When to Plan*: full plan, flat list, or skip.
3. For a full plan, scaffold `.plan/` via [init-plan.sh](./scripts/init-plan.sh).
4. Write the plan per the *Plan Template*, applying the quality, sizing, and task rules.
5. Run the *Verify* checklist against the finished plan.
6. Continue authorized implementation unless *Execution Handoff* identifies a material choice.

## Goal Quality Gate

Run this gate before *When to Plan* below — a weak goal wastes tokens on any path and produces an unverifiable result. Answer these five questions first:

1. **What concrete thing will be true when this is done?** (named artifact, system state verifiable without knowing the changed component's internals, or user-visible behavior — not "improve X" or "investigate Y")
2. **What evidence will prove it?** (specific test, command, screenshot, metric — not "looks right")
3. **What quantitative or binary threshold defines success?** (p95 < 250ms; `npm run test:checkout` passes; `gh pr view 123` shows no unresolved threads)
4. **What scope boundaries matter?** (which files/modules/environments are in scope; which are explicitly not)
5. **What should cause the agent to stop and ask?** (which decisions belong to the user, not Claude)

Then apply the Means test to the answer to question 1: **if the implementation changed, would this still be the goal?** If not, what was named is a Means, not the Objective. A request that supplies only an approach ("move the retry logic out of the controller into a job") passes all five questions while anchoring the plan to a mechanism -- and when the mechanism turns out wrong there is nothing left to re-derive the plan from. Recover the Objective from why the approach was proposed, keep the approach as the current best route, and record it as a decision rather than as the goal. An outcome-shaped Objective can still be a disguised mechanism -- apply the altitude test: could a reader who does not know the changed component's internals tell whether it was met? "X no longer holds the request open while it waits" fails that test; the real Objective is whatever depended on it ("checkout p95 under 300ms").

Apply a standalone-readability test as well: could a colleague who was not in this conversation state the goal from the Objective alone, without reading Scope, Key Decisions, or any later section? If the Objective only makes sense alongside later context, fold that context back into the Objective rather than leaving it to be reconstructed downstream.

Reject pure-activity goals ("make progress", "keep investigating", "improve things") -- repair them into a verifiable outcome or ask one concise clarification before planning. Skip this gate only when the request already names a specific artifact AND a clear success signal in the user's own words -- the same choice-free cases listed under *When to Plan* below. Anything vaguer than that runs the gate.

## When to Plan

Create a plan when it lowers implementation risk or preserves state that the current context cannot safely carry. A plan is a support artifact, not progress toward the requested capability.

- **Full plan** (`.plan/` directory): multi-phase work that crosses sessions or context limits, has interdependent decisions, or needs durable recovery state
- **Flat list** (inline checklist): clear multi-step work that fits in one session and has no durable decision record to preserve
- **Skip the plan artifact**: direct implementation with clear scope, known acceptance criteria, and no material unresolved choice

Treat file count, tool-call count, and new-feature status as signals, not triggers. Several mechanical files may need no plan, while one concurrency-sensitive file may need a written decision and verification strategy.

Stress-test apparently simple requests for hidden Key Technical Decisions (KTDs). *"Add caching to this endpoint"* hides TTL, invalidation, cache-key shape, and backend selection; record those decisions before implementation. A repository-wide rename can remain direct when it is mechanical and has an exhaustive verification command.

When skipping the plan artifact, proceed directly to implementation. Record only decisions that future work cannot re-derive cheaply, using the repository's existing decision-record convention.

## Planning Files

Scaffold the `.plan/` directory with pre-populated templates using [init-plan.sh](./scripts/init-plan.sh):

```bash
SKILL_DIR="<absolute path of the directory containing this SKILL.md>"
bash "$SKILL_DIR/scripts/init-plan.sh" "Feature Name"
```

Substitute the real absolute path before running; never execute the command with the angle-bracket placeholder. The script refuses to overwrite a `task_plan.md` that still has unchecked tasks -- that is the never-overwrite gate below; pass `--force` only after deciding which plan wins. Anchor the call to `SKILL_DIR` rather than a bare `init-plan.sh` — a relative path resolves against the caller's working directory, not the skill, and breaks from a subdirectory or under a non-Claude harness.

This creates `.plan/task_plan.md` and adds `.plan/` to `.gitignore`.

`.plan/` files are ephemeral working state -- do not commit them; old files are overwritten when starting a new feature. Before overwriting, check the existing `task_plan.md` for unchecked tasks: same work continuing means update in place, different work over an incomplete plan means stop and ask which plan wins -- never bulk-close or silently discard another plan's open items (the same rule applies to items mirrored into an external tracker). Within a multi-phase feature, use numbered intermediate files (`01-setup.md`, `02-phase1-complete.md`) to preserve state across phases. `docs/plans/` is the separate, committed home for a formal plan document; `.plan/` supports the work session.

| File | Purpose | Update When |
|------|---------|-------------|
| `.plan/task_plan.md` | Goal, decisions, next step, phases, discoveries that affect the plan, and errors that affect recovery | When a decision, phase state, or recovery point changes |

Do not create secondary findings or progress logs solely to prove activity. Add another planning artifact only when it carries state that `task_plan.md` cannot express clearly or when the user requested it as a deliverable.

## Test Discovery (Existing Projects)

For existing code, discover the test landscape before planning: find related test/spec files (`Glob("**/*test*")`, `Grep`), read the canonical test command from config (`package.json` scripts, `pytest.ini`, `phpunit.xml`, CI), and note coverage gaps -- the plan should extend existing test patterns, not introduce new frameworks. Skip for greenfield projects with no tests yet.

## Reference Implementations

When target behavior is hard to describe but an existing implementation embodies it, cite that source as the spec and plan to reimplement its *semantics* -- source code is higher-fidelity than prose, docs, or screenshots. Record a `ref:` pointer in the plan so the implementer reads the source, not a summary. Full guidance in [execution-and-methodology.md](./references/execution-and-methodology.md).

## Plan Template

```markdown
# Plan: [Feature/Task Name]

**Spec:** [optional -- path or URL to the spec/design doc this plan implements; distinct from a `ref:` pointer, which names a reference implementation to reimplement, not a spec to satisfy]

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
**Files**: [specific files owned by this phase]
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
- [Only genuinely blocking unknowns]
```

### Plan Quality Rules

**Keep phase state current.** Changing a phase's `Status` also refreshes `## Next Step`. That one line is what the resume protocol reads after a compaction or a new session, so a stale `Next Step` is worse than none -- it resumes work that already happened.

**No placeholders in tasks.** Every task must contain actual code patterns, commands, or file paths. Forbid: "TBD", "TODO", "handle errors appropriately", "add validation", "implement as needed", "similar to above", "Similar to Task N", "See above." Tasks may be read out of order -- repeat the spec, code pattern, or file path in every task that needs it. A step that cannot be specified concretely needs further breakdown before it belongs in a plan.

**Type-consistency check.** After writing all tasks, scan for naming drift. If Task 3 says `clearLayers()` but Task 7 says `clearFullLayers()`, that's a bug in the plan. Function names, variable names, and file paths must be consistent across all tasks.

**No gold-plating.** Build exactly what the spec requires -- no features or "nice-to-haves" beyond it. Quote the exact spec requirements in the plan and flag any additions explicitly as scope expansion needing approval.

**Keep the deliverable ahead of the apparatus.** Every process or operations item names the capability or observed defect class it gates. Stop adding checks, matrices, or plan structure when the existing machinery is sufficient to keep implementation honest. Record deferred rigor as debt rather than building it speculatively.

**Do not edit the target down to the implementation.** A plan or specification change needs independent product or technical justification. A weaker acceptance criterion is not a fix for code that fails the original one.

**Keep closures vertical.** Internal plan steps may isolate one action, but a closable phase or external work item includes its implementation and tests and ends in runnable behavior. Do not turn types, implementation, tests, and documentation for one capability into separate completion credits.

**Front-load high-variance decisions.** Order the plan document by how likely each part is to change on review, not by execution order -- the template's *Key Decisions* bracket defines what goes there; execution order still governs the phases themselves.

## Phase Sizing Rules

Every phase must be **context-safe**:

- End in one coherent, independently verifiable capability or integration state.
- Fit in the available context, or record a clear recovery boundary before compaction or handoff.
- Name dependencies whose failure would block the phase.
- Split only when each part has a meaningful verification boundary; do not split to meet a file, task, or duration target.
- Challenge scope when nonlocal invariants, ownership overlap, or integration dependencies make independent delivery unlikely.

## Task Decomposition

Decompose by user-visible capability (vertical slices), not by technical layer, so each phase is independently demonstrable. Checkpoint where components first integrate, before an irreversible transition, and before phase closure. Full guidance -- vertical slicing and the checkpoint system -- in [execution-and-methodology.md](./references/execution-and-methodology.md).

## Decision Authority

Not every decision needs user input:

**Claude decides (technical implementation):** language, framework, architecture, libraries, file structure, naming conventions, test strategy, error handling approach, database schema details, API design patterns. Make the call, document the rationale in the plan.

**User decides (experience-affecting):** scope tradeoffs ("cut X to hit deadline?"), UX choices that change what users see or do, data model decisions that constrain future product options, anything where two valid paths lead to meaningfully different user outcomes.

**Heuristic:** If the decision changes what the user *experiences*, ask. If it changes how the code *works*, decide.

## Clarifying Questions

Ask via AskUserQuestion (Claude Code; load with ToolSearch `select:AskUserQuestion` if not loaded) or request_user_input (Codex); fall back to numbered options in chat.

Ask only about decisions that fall in the "user decides" category above. Batch the material unknowns, and make reasonable assumptions for everything else. Do not manufacture a question count from task size.

## Task Rules

Write every task as if the implementer has zero context and questionable taste -- they cannot infer intent from conversation history, so everything must be in the plan.

- **Atomic**: one independently verifiable action. Internal steps may separate test setup from implementation, but they do not become separately closable work items.
- **Verb-first**: "Add...", "Create...", "Refactor...", "Verify..."
- **Concrete**: name specific files, endpoints, components, and verification. Include code patterns or line-level anchors only when they preserve a decision the implementer could not recover cheaply.
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

When the user requested a plan only, stop after delivering the plan. When the request already authorizes implementation, continue with the simplest execution mode that fits the work. Ask the user to choose between inline and delegated execution only when the choice materially changes cost, risk, isolation, or review quality. Dispatch discipline and portable task-prompt anchoring are in [execution-and-methodology.md](./references/execution-and-methodology.md).

## Verify

- Plan file exists at `.plan/task_plan.md` (or `docs/plans/` for formal plans)
- All tasks are verb-first and independently verifiable
- File structure and ownership are explicit where they affect integration
- Phase boundaries follow runnable capability and context safety rather than file or task counts
- No placeholder tasks ("implement feature", "add tests") -- every task names specific files and patterns
- Each phase delivers end-to-end functionality (not a single horizontal layer)
- Every process item names the capability or observed defect class it gates
- Open questions contain only genuinely blocking unknowns

## Integration

- **Predecessor:** `ia-brainstorming` when requirements are ambiguous -- use an existing brainstorm spec (`docs/brainstorms/`) as input and skip idea refinement.
- **Architecture decisions:** record significant trade-offs (chosen approach, what was given up) as an ADR (`/ia-adr` in Claude Code); ADRs outlive the plan.
- **Threat modeling:** dispatch `ia-security-sentinel` in threat-model mode before implementation when the plan adds auth flows, payment handling, external API surfaces, or new trust boundaries -- architectural gaps are cheaper to fix in the plan than the code.
- **Prose quality:** `ia-writing` to humanize plan language and strip AI slop.
- **Execution handoff:** continue authorized work or ask only when the execution-mode choice is material, per *Execution Handoff* above.
