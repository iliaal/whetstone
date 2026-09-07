# goal definition

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
3. For a full plan, scaffold `.plan/` via [init-plan.sh](../scripts/init-plan.sh).
4. Write the plan per the [plan template](./plan-format.md#plan-template), applying the quality, sizing, and task rules.
5. Run the [Verify checklist](../SKILL.md#authority-and-verification) against the finished plan.
6. Continue authorized implementation unless [Execution handoff](./execution-handoff.md#execution-handoff) identifies a material choice.

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
