# task design

## Phase Sizing Rules

Every phase must be **context-safe**:

- End in one coherent, independently verifiable capability or integration state.
- Fit in the available context, or record a clear recovery boundary before compaction or handoff.
- Name dependencies whose failure would block the phase.
- Split only when each part has a meaningful verification boundary; do not split to meet a file, task, or duration target.
- Never state hour, day, or week estimates in a plan; an agent has no wall-clock experience, so such figures are confabulated. Size by dependency count, verification steps, and a relative Small/Medium/Large label instead.
- Challenge scope when nonlocal invariants, ownership overlap, or integration dependencies make independent delivery unlikely.

## Task Decomposition

Decompose by user-visible capability (vertical slices), not by technical layer, so each phase is independently demonstrable. Checkpoint where components first integrate, before an irreversible transition, and before phase closure. Full guidance (vertical slicing and the checkpoint system) is in [execution-and-methodology.md](./execution-and-methodology.md).

## Decision Authority

Not every decision needs user input. Apply the following division within existing user choices, repository constraints, and authorized scope; technical work can still require a material user decision:

**Claude decides (technical implementation):** language, framework, architecture, libraries, file structure, naming conventions, test strategy, error handling approach, database schema details, API design patterns. Make the call, document the rationale in the plan.

**User decides (experience-affecting):** scope tradeoffs ("cut X to hit deadline?"), UX choices that change what users see or do, data model decisions that constrain future product options, anything where two valid paths lead to meaningfully different user outcomes.

**Heuristic:** If the decision changes what the user *experiences*, ask. If it changes how the code *works*, decide.

## Clarifying Questions

Ask via AskUserQuestion (Claude Code; load with ToolSearch `select:AskUserQuestion` if not loaded) or request_user_input (Codex); fall back to numbered options in chat.

Ask only about decisions that fall in the "user decides" category above. Batch the material unknowns, and make reasonable assumptions for everything else. Do not manufacture a question count from task size.

## Task Rules

Write every task as if the implementer has zero context and questionable taste: they cannot infer intent from conversation history, so everything must be in the plan.

- **Atomic**: one independently verifiable action. Internal steps may separate test setup from implementation, but they do not become separately closable work items.
- **Verb-first**: "Add...", "Create...", "Refactor...", "Verify..."
- **Concrete**: name specific files, endpoints, components, and verification. Include code patterns or line-level anchors only when they preserve a decision the implementer could not recover cheaply.
- **Ordered**: respect dependencies, sequential when needed
- **Verifiable**: include at least one validation task per phase
- **Complete**: do not defer test coverage, skip edge cases, or omit error handling to save time. The marginal cost of completeness during initial implementation is near-zero compared to retrofitting later.
