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

Produce the smallest plan that reduces implementation risk and preserves state costly to reconstruct. User requirements and verified facts govern the plan; a reference implementation supplies evidence about behavior, not independent authority to change scope.

## Procedure

1. Define the concrete outcome, evidence, binary or quantitative success threshold, scope boundaries, and stop conditions. If the request already names an artifact and success signal, use them. Otherwise repair activity-only goals before planning.
2. Separate the objective from the proposed mechanism: would the goal remain valid if the implementation changed? Ensure a colleague can understand the objective alone and verify it without knowing component internals.
3. Choose a full durable plan for interdependent phases, recovery needs, or work crossing context limits; an inline list for clear work fitting one session; direct implementation for clear scope and acceptance criteria. File and tool-call counts are signals, not triggers. Inspect hidden decisions such as cache TTL, invalidation, and key shape before treating work as simple.
4. Inspect existing tests, canonical commands, related code, and any existing brainstorm specification. Extend repository patterns. Record significant architectural tradeoffs in its ADR convention when needed.
5. Define files, ownership, interface contracts, dependencies, concrete tasks, verification, and exit conditions. Organize phases around runnable capabilities with implementation and tests together. Put high-variance decisions before mechanical work; keep execution dependencies in phase order.
6. Verify the plan against the user's requirements. Keep phase status and next step consistent. Never weaken acceptance criteria to match incomplete code or add speculative checks and machinery.
7. Deliver the plan when planning alone was requested. Continue implementation when already authorized. Ask about execution mode only if it materially changes cost, risk, isolation, or review quality.

## Durable state

For a full working plan, read [plan-format.md](./references/plan-format.md) and scaffold with [init-plan.sh](./scripts/init-plan.sh), anchored to the installed skill directory rather than the caller's working directory. When the project already uses a spec or plan system, keep that system's artifact format; the skill owns the clarification, content, and approval gates, not the representation. Otherwise, use `.plan/task_plan.md` for uncommitted session state and `docs/plans/` for a formal committed plan.

Inspect an existing plan before overwriting it. Continue the same work in place; ask which plan wins when different work would displace unchecked tasks. Never silently discard or bulk-close open work, including tracker items. Use `--force` only after resolving that choice. Add secondary artifacts only for requested deliverables or state the main plan cannot express clearly.

## Conditional guidance

- For vague goals, a proposed mechanism disguised as an objective, or choosing planning depth, read [goal-definition.md](./references/goal-definition.md).
- For a full plan, template, test discovery, source pointers, or plan-quality review, read [plan-format.md](./references/plan-format.md). Preserve exact specification values and name concrete paths or commands in every task.
- When decomposing phases, setting ownership, or deciding what needs clarification, read [task-design.md](./references/task-design.md). Respect existing user choices and project constraints before selecting technical details. Escalate materially different outcomes or authority gaps; routine implementation choices stay with the implementer.
- For vertical slicing, checkpoints, reference semantics, phase posture, or delegated execution, read [execution-and-methodology.md](./references/execution-and-methodology.md).
- When starting multi-phase work or resuming after a gap, read [operational-patterns.md](./references/operational-patterns.md) for recovery, context checks, and error handling.
- When deepening an existing plan, read [plan-deepening.md](./references/plan-deepening.md); preserve its structure and add targeted research.
- When selecting execution posture, handing off, or integrating related skills, read [execution-handoff.md](./references/execution-handoff.md).

## Authority and verification

Use the active harness's question tool when its schema and context permit; otherwise ask in chat. Batch material unknowns, make safe assumptions for routine details, and never manufacture a question count.

Verify that each task is verb-first, concrete, independently verifiable, and comprehensible without conversation history. Check naming and interface consistency across tasks. Every phase needs a runnable capability, explicit verification, and a context-safe recovery boundary; process items must name the capability or observed defect they gate. Open questions contain only blocking unknowns. A plan artifact does not itself establish implementation progress.

For ambiguous requirements use `ia-brainstorming`; for significant new trust boundaries, auth, payments, or external APIs, obtain the applicable security threat-model review before implementation. Use `ia-writing` for prose. Report the plan location, material decisions, and remaining blockers without claiming unexecuted checks passed.
