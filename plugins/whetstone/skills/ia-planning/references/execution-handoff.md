# execution handoff

## Operational Patterns

Context management rules, error protocol (3-attempt escalation), iterative plan refinement, the 5-question context check, and session-continuity/traceability conventions (numbered outputs, resume protocol, SHA and deviation notes) are in [operational-patterns.md](./operational-patterns.md). Read when starting a multi-phase plan or resuming after a gap.

## Execution Posture Signals

Phases can carry optional metadata that shapes how `/ia-work` sequences implementation. Default is tests-after; opt in per phase via the header (`## Phase 2: Auth middleware [test-first]`): `test-first` (write failing test before implementation), `characterization-first` (capture existing behavior before changing it), `external-delegate` (mark units suitable for parallel/external execution). When to use each is in [execution-and-methodology.md](./execution-and-methodology.md).

## Plan Deepening

When asked to "deepen" or "strengthen" an existing plan, load [plan-deepening.md](./plan-deepening.md) — targeted research workflow (additive, not restructuring), per-section enhancement format, and Enhancement Summary block at the plan head. Orchestrated by the `/ia-deepen-plan` command.

## Execution Handoff

When the user requested a plan only, stop after delivering the plan. When the request already authorizes implementation, continue with the simplest execution mode that fits the work. Ask the user to choose between inline and delegated execution only when the choice materially changes cost, risk, isolation, or review quality. Dispatch discipline and portable task-prompt anchoring are in [execution-and-methodology.md](./execution-and-methodology.md).

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
