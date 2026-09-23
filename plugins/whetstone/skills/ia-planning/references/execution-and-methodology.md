# Execution & Decomposition Patterns

Load when decomposing a plan into slices, annotating phases with execution postures, handing an approved plan off to implementation, or specifying behavior against an existing reference implementation.

## Reference Implementations

When an authorized reference implementation embodies target behavior, cite its source to preserve exact semantics and edge cases that a summary may omit. Treat it as evidence subordinate to governing requirements, not a replacement specification; existing bugs do not become requirements merely because the source contains them. Name the file or module and the behavior to match, resolve conflicts against user requirements, and plan to reimplement the *semantics* rather than copy code verbatim, including across languages. Record the pointer so the implementer reads the source: `ref: legacy/pricing.py -> reimplement the specified pricing semantics in src/pricing.ts`.

## Task Decomposition

### Vertical slicing

Decompose by user-visible capability, not by technical layer. "User can log in" is a vertical slice: it touches UI, API, and DB, and delivers a working feature when done. "Build the auth database schema" is a horizontal slice that delivers zero value until other slices complete.

Vertical slices are independently demonstrable and testable. Each slice should produce something a stakeholder can see, try, or verify. When a phase in a plan delivers only one layer (all models, all controllers, all views), restructure it into slices that cut through all layers for one capability at a time.

### Checkpoint system

Pause and verify when completed pieces first cross an integration boundary, before an irreversible transition, and before phase closure. Run the narrowest test or user path that proves the pieces work together. This catches drift without turning task count into a ceremony trigger.

Checkpoints are lightweight: run the test suite, hit the endpoint, render the component. Not a formal review. The goal is a fast feedback signal: "everything built so far integrates correctly." Record a result in `task_plan.md` only when it changes phase state or matters for recovery.

## Execution Posture Signals

Plans can carry lightweight metadata per phase that shapes how `/ia-work` sequences implementation. These are optional annotations, not requirements.

**Default**: tests-after. `/ia-work` writes tests alongside implementation for new features. No posture signal needed in this case.

Opt-in postures for phases that need different sequencing:

- **test-first**: Write failing tests before implementation. Use when behavior is well-defined and testable upfront (bug fixes always qualify; new features qualify when the contract is clear before coding).
- **characterization-first**: Capture existing behavior with tests before changing it. Use when modifying code without existing test coverage.
- **external-delegate**: Mark self-contained units suitable for parallel execution (separate worktree, separate agent). Use when a phase has no dependencies on other phases.

Add posture signals in the phase header: `## Phase 2: Auth middleware [test-first]`. The executor inherits these silently without interrupting questions; they shape sequencing, not scope.

## Execution Handoff

When a plan-only request is complete, deliver the plan and stop. When implementation is already authorized, choose the simpler of these execution modes unless the choice materially changes cost, risk, isolation, or review quality:

1. **Subagent-driven** (recommended for multi-phase plans, independent slices, or worktree-isolated work): dispatch each phase to a focused subagent with a self-contained task prompt (Objective / Owned Files / Interface Contracts / Acceptance Criteria / Out of Scope / Validation Assignment). Orchestrator integrates results and verifies between phases. See `ia-orchestrating-swarms` for dispatch discipline. Anchor each task prompt portably (repo/package names, public symbols, command names, config keys, branch and PR/issue references, exact error text, and relative file paths, not absolute ones, which vary across working directories) so a fresh agent starting in a different working directory can resolve every reference.
2. **Inline execution**: main session runs the plan phase by phase. Use when phases are tightly coupled, require shared context that would be expensive to rehydrate, or the total work fits in one session without compaction risk.

Ask the user to choose only when the execution-mode trade-off is material. Otherwise continue with the selected mode and keep the plan's `## Next Step` current.
