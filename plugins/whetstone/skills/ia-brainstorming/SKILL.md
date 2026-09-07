---
name: ia-brainstorming
class: workflow
description: >-
  Pre-implementation exploration: deep interview, approach comparison, design
  doc. Use when exploring a vague feature idea, clarifying ambiguous
  requirements, or comparing approaches before coding. For the full workflow,
  use the ia-brainstorm command (Claude Code).
---

# Brainstorming

Clarify what to build before planning how to implement it.

## Scope and interaction

Produce exploration and a design, not implementation. Obtain approval before interactive handoff. Enable headless mode only when the caller explicitly delegates non-interactive execution and its decision scope; `disable-model-invocation` is selection metadata, not approval. Replace headless confirmations with stated conservative assumptions. Return material decisions without a safe authorized default unresolved. Never label inferred choices user-approved or infer implementation, commit, or publication authority from this skill.

Use the active question mechanism for material questions: AskUserQuestion in Claude Code (load via ToolSearch `select:AskUserQuestion` when needed), request_user_input in Codex where supported, otherwise chat. Return missing decisions to the parent from an unattended worker.

## Process

1. **Assess and ground.** For an existing project, read relevant code, documentation, constraints, and recent commits before questions. Surface contradictions between the request and observed behavior. Skip repository research for abstract topics. Brainstorm ambiguous goals, competing interpretations, unresolved trade-offs, uncertain needs, solution-framed requests, or multiple independent subsystems. If requirements are clear, suggest planning or implementation without forcing dialogue.
2. **Right-size and decompose.** A brainstorm resolved in three messages may need only a summary; sustained architectural work needs a durable design. For multiple independent subsystems, identify boundaries and dependencies, choose build order, then give each sub-project its own design → plan → implementation cycle. Start with the first sub-project.
3. **Understand and compare.** When dialogue or approach selection is needed, read [interview-and-approaches.md](./references/interview-and-approaches.md). Match the user's vocabulary. Normally ask one question across dimensions, or two to three within one dimension; for a substantial initial dump (>200 words), use the reference's bounded batch. Explore purpose, users, constraints, success, edge cases, patterns, and non-goals. Apply [deep-interview.md](./references/deep-interview.md) when assumptions, evidence, unfamiliar domains, or combined answers need probing; its integration check applies before interview exit. Stop questioning when clear or told to proceed. Summarize in three to five bullets and confirm in interactive mode.
4. **Choose an approach.** Compare two to three concrete alternatives with descriptions, pros, cons, and best-use conditions. Lead with the recommendation, reference existing patterns, and expose trade-offs. If none is accepted after two rounds, ask for the preferred direction. For a wide design space, use two to three lenses from the approach reference. State the chosen approach's explicit Not Doing list and a validation method for every key assumption.
5. **Confirm interpreted scope.** Before writing after substantive dialogue, read [scope-synthesis.md](./references/scope-synthesis.md). Separate stated requirements, inferred assumptions, and exclusions internally; present only the reference's concise scoping synthesis. Lightweight work without blocking questions uses announce-mode; Standard/Deep work or any blocking dialogue requires interactive confirmation. Re-present revisions and await confirmation. In headless mode preserve sources and unresolved assumptions without prompts. Clear requirements that skipped dialogue need no synthesis checkpoint.
6. **Capture and self-review.** For a durable artifact, read [design-and-handoff.md](./references/design-and-handoff.md). Save `docs/brainstorms/YYYY-MM-DD-<topic>-brainstorm.md` with date/topic frontmatter, What We're Building, Why This Approach, Key Decisions and rationale, Open Questions, and Next Steps. Collapse interview history in a details block. Describe each component's purpose, usage, dependencies, and testable boundary. Commit only within caller authority.
7. **Handoff.** Preserve settled decisions and their rationale rather than repeatedly challenging them; a cold directive gets one approach challenge. Neither label suppresses concrete defect or infeasibility evidence. Require consistent terminology, concrete criteria, scope traceability, unambiguous decisions, explicit non-goals, assumption validation, and a named source for every produced value. Return failures to approach selection or drafting. Present the design for interactive approval; return caller-delegated decisions and unresolved assumptions in headless mode.

## Completion

Return the scoped summary or saved design path, decisions, and open questions resolved or explicitly deferred with reasons. Interactive approval precedes handoff; a headless handoff remains within caller authority. Planning (`ia-planning`, or `/ia-plan` in Claude Code) follows design and reuses its settled requirements. For auth, payments, external APIs, or multi-tenant data, suggest an available security threat-model review before planning.
