---
name: lfg
description: Full autonomous engineering workflow (plan, build, review, ship)
argument-hint: "[feature description] [--swarm for parallel execution]"
disable-model-invocation: true
---

Run these steps in order. Do not stop between steps -- complete every step through to the end.

**Mode detection:** If `$ARGUMENTS` contains `--swarm`, use swarm mode (parallel execution in steps 4-6). Otherwise run sequentially.

## Sequential steps

1. `/workflows:plan $ARGUMENTS` (strip `--swarm` from arguments if present)
2. `/compound-engineering:deepen-plan`

## Build

3. `/workflows:work`

**Swarm mode:** Use Task list and launch parallel agent swarm subagents to build the plan.
**Normal mode:** Execute sequentially.

## Verify (parallel in swarm mode)

4. `/workflows:review`
5. `/compound-engineering:test-browser`

**Swarm mode:** Launch steps 4 and 5 as parallel background Task agents. Wait for both to complete.
**Normal mode:** Run sequentially.

## Finalize

6. `/compound-engineering:resolve_todo_parallel` -- resolve any findings from review
7. `/compound-engineering:feature-video` -- record walkthrough and add to PR

Start now.
