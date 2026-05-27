---
name: ia-lfg
description: Full autonomous engineering workflow (plan, build, review, ship)
argument-hint: "[feature description] [--swarm for parallel execution]"
disable-model-invocation: true
---

Run these steps in order. Do not stop between steps -- complete every step through to the end.

**Mode detection:** If `$ARGUMENTS` contains `--swarm`, use swarm mode (parallel execution in steps 4-6). Otherwise run sequentially.

**Arguments guard:** If `$ARGUMENTS` is empty (no feature description and no `--swarm`), ask for a feature description before proceeding. Do not invoke `/ia-plan` with empty input.

## Sequential steps

1. `/ia-plan $ARGUMENTS` (strip `--swarm` from arguments if present)
2. `/ia-deepen-plan` (auto-detects latest plan in `docs/plans/`)

## Build

3. `/ia-work`

**Swarm mode:** Use Task list and launch parallel agent swarm subagents to build the plan.
**Normal mode:** Execute sequentially.

## Verify (parallel in swarm mode)

4. `/ia-review`
5. `/ia-test-browser`

**Swarm mode:** Launch steps 4 and 5 as parallel background Task agents. Wait for both to complete.
**Normal mode:** Run sequentially.

## Finalize

6. `/ia-resolve-todo-parallel` -- resolve any findings from review
7. `/ia-feature-video` -- record walkthrough and add to PR

## CI watch (after PR opens)

8. **Before polling: distinguish actionable CI failures from non-actionable gates.** Run `gh pr view --json isDraft,reviewDecision` plus `gh pr checks --json name,state,bucket,conclusion`. Classify by check conclusion, not vendor name:
    - Check `conclusion: failure` on a required status check -> actionable, fix in Step 9.
    - `isDraft: true` with no checks after a grace period -> stop and report `DRAFT_PR_WITH_NO_CHECKS`. Do not mark ready for review unless asked.
    - `reviewDecision: REVIEW_REQUIRED` or any human-approval gate with no failing checks -> stop and report `BLOCKED_BY_REVIEW_GATE`. Human review is not an actionable failure.
    - No checks registered after a grace period -> stop and report `NO_CHECKS_REGISTERED`.
    - Check `conclusion: neutral`/`skipped` or pending non-required checks -> do not wait. Required-status-checks (configurable via `gh api repos/{owner}/{repo}/branches/{branch}/protection`) are the source of truth; common examples include test/lint/build jobs and code-review bots (Sentry, Codecov, Cursor, BugBot, etc.) — treat each by its conclusion, not its name.
9. Poll CI for the new PR. On failure: read the job log, identify the root cause, fix, push. Cap at **3 fix iterations**.
10. Do **NOT** weaken, skip, or mock the failing assertion to make CI green -- repair the actual issue. If genuinely flaky after 3 iterations, document the residual in the PR body and stop.

Start now.
