---
name: lfg
description: Full autonomous engineering workflow (plan, build, review, ship)
argument-hint: "[feature description] [--swarm for parallel execution]"
disable-model-invocation: true
---

Run these steps in order. Do not stop between steps -- complete every step through to the end.

**Mode detection:** If `$ARGUMENTS` contains `--swarm`, use swarm mode (parallel execution in steps 4-6). Otherwise run sequentially.

**Arguments guard:** If `$ARGUMENTS` is empty (no feature description and no `--swarm`), ask for a feature description before proceeding. Do not invoke `/workflows:plan` with empty input.

## Sequential steps

1. `/workflows:plan $ARGUMENTS` (strip `--swarm` from arguments if present)
2. `/deepen-plan` (auto-detects latest plan in `docs/plans/`)

## Build

3. `/workflows:work`

**Swarm mode:** Use Task list and launch parallel agent swarm subagents to build the plan.
**Normal mode:** Execute sequentially.

## Verify (parallel in swarm mode)

4. `/workflows:review`
5. `/test-browser`

**Swarm mode:** Launch steps 4 and 5 as parallel background Task agents. Wait for both to complete.
**Normal mode:** Run sequentially.

## Finalize

6. `/resolve-todo-parallel` -- resolve any findings from review
7. `/feature-video` -- record walkthrough and add to PR

Start now.
