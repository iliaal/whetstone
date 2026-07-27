# Execution & Decomposition Patterns

Load when decomposing a plan into slices, annotating phases with execution postures, handing an approved plan off to implementation, or specifying behavior against an existing reference implementation.

## Reference Implementations

When the target behavior is hard to describe in prose but an existing implementation already embodies it, cite that implementation as the spec instead of paraphrasing it. Source code is a higher-fidelity reference than a doc, diagram, or screenshot -- it pins exact semantics, edge-case handling, and structure that prose drops. Name the file or module, state what to match, and plan to reimplement the *semantics* (not copy the code verbatim) in the target stack, even when the reference is in a different language. Record the pointer in the plan so the implementer reads the source, not a summary of it: `ref: legacy/pricing.py -> reimplement semantics in src/pricing.ts`.

## Task Decomposition

### Vertical slicing

Decompose by user-visible capability, not by technical layer. "User can log in" is a vertical slice -- it touches UI, API, and DB, and delivers a working feature when done. "Build the auth database schema" is a horizontal slice that delivers zero value until other slices complete.

Vertical slices are independently demonstrable and testable. Each slice should produce something a stakeholder can see, try, or verify. When a phase in a plan delivers only one layer (all models, all controllers, all views), restructure it into slices that cut through all layers for one capability at a time.

### Checkpoint system

After every 2-3 completed tasks, pause and verify: are the completed pieces actually working together? Run tests, check integration points, confirm that data flows end-to-end. This catches drift early instead of discovering at the end that pieces don't fit.

Checkpoints are lightweight -- run the test suite, hit the endpoint, render the component. Not a formal review. The goal is a fast feedback signal: "everything built so far integrates correctly." Document checkpoint results in `.plan/progress.md`.

## Execution Posture Signals

Plans can carry lightweight metadata per phase that shapes how `/ia-work` sequences implementation. These are optional annotations, not requirements.

**Default**: tests-after -- `/ia-work` writes tests alongside implementation for new features. No posture signal needed in this case.

Opt-in postures for phases that need different sequencing:

- **test-first**: Write failing tests before implementation. Use when behavior is well-defined and testable upfront (bug fixes always qualify; new features qualify when the contract is clear before coding).
- **characterization-first**: Capture existing behavior with tests before changing it. Use when modifying code without existing test coverage.
- **external-delegate**: Mark self-contained units suitable for parallel execution (separate worktree, separate agent). Use when a phase has no dependencies on other phases.

Add posture signals in the phase header: `## Phase 2: Auth middleware [test-first]`. The executor inherits these silently without interrupting questions -- they shape sequencing, not scope.

## Execution Handoff

When a plan is complete and ready to execute, offer the user an explicit choice rather than drifting into implementation. Present two options:

1. **Subagent-driven** (recommended for multi-phase plans, independent slices, or worktree-isolated work): dispatch each phase to a focused subagent with a self-contained task prompt (Objective / Owned Files / Interface Contracts / Acceptance Criteria / Out of Scope / Validation Assignment). Orchestrator integrates results and verifies between phases. See `ia-orchestrating-swarms` for dispatch discipline. Anchor each task prompt portably -- repo/package names, public symbols, command names, config keys, branch and PR/issue references, exact error text, and relative file paths (not absolute, which vary across working directories) -- so a fresh agent starting in a different working directory can resolve every reference.
2. **Inline execution**: main session runs the plan phase by phase. Use when phases are tightly coupled, require shared context that would be expensive to rehydrate, or the total work fits in one session without compaction risk.

State the recommendation with a one-sentence reason, then wait for the user to pick. Do not auto-start either path -- drifting from "plan approved" to "plan in progress" without the user picking a handoff mode is how orchestration discipline silently decays.
