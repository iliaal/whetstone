# worker lifecycle

**One implementation unit per worker.** A worker dispatched to implement a unit gets a fresh context and is retired once that unit is integrated -- never retasked onto a second unit, never held as an idle pool. The same handle may continue or recover *its own* unit (the crash-relaunch path below). Persistent teammates are exempt. Scope, exemptions, and workspace-cleanup rules: [orchestration-patterns.md](./orchestration-patterns.md) (One implementation unit per worker).

**Preset team compositions:** Start from a named preset before designing a custom team. See [team-compositions.md](./team-compositions.md) for the conceptual Review / Debug / Feature / Fullstack / Migration / Security / Research compositions. Its `subagent_type` fields are Claude-specific; in Codex, express the same read-only or implementation boundary in the task prompt and available permissions.

**Model selection by task complexity:** Apply explicit model arguments only when the active harness exposes them and session instructions permit them. The examples below are Claude-specific; inspect the active Codex schema rather than assuming a fixed argument set.

| Task shape | Model |
|-----------|-------|
| Mechanical, clear spec, no hidden invariants | `model: "haiku"` |
| Multi-file integration, standard complexity | Default model |
| Architecture decisions, ambiguous scope, review | `model: "opus"` |

Key the choice on reasoning difficulty, not size: file count, agent count, and wave width are not model triggers. A large mechanical rename stays cheap; a single-file change to a concurrency invariant does not. Escalate for nonlocal invariants, concurrency or state machines, migrations, parsing, auth and security, retry/error semantics, or public API and data-contract changes.

**Handoff protocol -- structured agent-to-agent transfers.** When passing work between agents (leader→implementer, implementer→reviewer, reviewer→leader), include:
1. **Context**: what was done, relevant files, constraints discovered
2. **Deliverable**: specific output expected from the receiving agent
3. **Acceptance criteria**: how the receiving agent knows the work is correct

The controller reads all tasks from the plan upfront and provides full task text directly to subagents. Do not make subagents hunt plan files for their assignment; paste the task content into the prompt. The only exception is the disk handoff contract in [resilience-patterns.md](./resilience-patterns.md) (Orchestrator context exhaustion mid-pipeline), where the brief still names the exact file the leaf reads. Skill availability varies by harness and agent context, so a skill name alone is not an adequate brief. Inline the specific operative instructions; when a worker needs further skill guidance, provide its accessible location and let it inspect that source. When the active harness auto-injects the project's instruction file (`CLAUDE.md`, `AGENTS.md`) into subagents, do not restate it or paste its rules into the brief; name only the specific rule the task needs. That exception covers only the project instruction file; the brief still carries every task-operative instruction. This is harness-dependent: some built-in agent types and other harnesses do not inject it, and a worker there gets only what the brief carries. See [handoff-templates.md](./handoff-templates.md) for QA FAIL and Escalation Report formats.

**The orchestrator mints identifiers; workers never do.** Models cannot compute hashes for dedupe IDs, and hashing a model-authored field forks identity on wording changes. See [cross-run-coordination.md](./cross-run-coordination.md) (Identifier minting section).

**Standardize implementer outcome signals.** Require every implementer to distinguish completed and verified behavior from partial work, stubs, mocks, refusal-only paths, and blockers. Do not require empty report sections. Route blockers through the decision tree below.

**Worker status vocabulary:** `DONE` (task verified complete) | `DONE_WITH_CONCERNS` (complete, residual risk named) | `BLOCKED` (blocker stated, no partial claim) | `NEEDS_CONTEXT` (missing information named). Callers that require a structured return (`/ia-resolve-todo-parallel`, `/ia-work`) use this vocabulary; free-form reports elsewhere still distinguish the same states in prose.

Partial work, a stub, a mock, a refusal-only path, or an unverifiable deliverable maps onto that vocabulary as `DONE_WITH_CONCERNS` when the delivered part is itself verified and the gap is named in the report, and `BLOCKED` otherwise -- never `DONE`.

**BLOCKED triage decision tree** -- when a teammate reports BLOCKED, classify the root cause before acting. Never retry the same prompt on the same model without changing a variable.

| Root cause | Signal | Response |
|-----------|--------|----------|
| Missing context | Agent asked for a file, spec, or decision it needed | Provide the missing context, re-dispatch same agent |
| Reasoning ceiling | Agent attempted, got stuck on a subtlety it cannot resolve | If supported, escalate the model; otherwise narrow the task or provide stronger evidence and re-dispatch |
| Task too large | Agent made partial progress but hit token/complexity limits | Split into smaller tasks with explicit interface contracts |
| Spec wrong | Agent surfaces a contradiction in the plan or a missing requirement | Escalate to the user -- do not re-dispatch |

Never ignore an escalation. Never force the same agent to retry without changing at least one variable (context, model, or task scope).

**An agent that crashed or timed out without returning a usable result is a different case, and the working tree decides the response.** Inspect its owned files for partial edits first (`git status`, `git diff`): a clean tree is an ordinary retry; a dirty tree gets exactly one relaunch whose prompt names the touched files and instructs verify-and-continue, never redo. That relaunch is a retry of the same agent, not a new agent against the dispatch budget, and a second crash for the same agent is a hard stop: report it. Neither a crash nor a timeout licenses calling the run an infrastructure failure to justify a free retry. Why redo double-applies, and the declared-handoff-artifact variant: [resilience-patterns.md](./resilience-patterns.md). An agent-reported BLOCKED answered, so it routes to the table above.
