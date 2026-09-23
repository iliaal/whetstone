# claims and failures

## When This Applies

- About to claim "tests pass", "build succeeds", or "bug fixed"
- About to commit, push, create a PR, or mark a task complete
- Before closing a phase or work item
- Reporting results to the user
- A subagent reports success on delegated work

## Red Flags

**Clean results do not require manufactured findings.** A first pass with zero issues is valid when the evidence covers the stated acceptance criteria and relevant failure paths. Broaden verification only when the current proof leaves a named risk untested.

**Do not inflate the claim.** Name the proof scope when it is narrower than the natural reading of the completion claim. A targeted test supports the named behavior; only the full suite supports a full-suite claim.

## Requirements vs Tests

"Tests pass" and "requirements met" are different claims: re-read the plan or requirements, create a line-by-line checklist, verify each item against the implementation, then report gaps or confirm completion. Passing tests prove the code works, not that the right code was written.

## Common Claims and Their Proof

| Claim | Required Proof |
|-------|---------------|
| "Tests pass" | Test runner output showing 0 failures, exit code 0 |
| "Build succeeds" | Build command output with exit code 0 |
| "Bug is fixed" | Original reproduction case now passes |
| "Feature complete" | All acceptance criteria verified individually |
| "No regressions" | Full test suite passes, not just new tests |
| "Regression test works" | Red-green cycle: test passes, revert fix, test fails, restore fix, test passes |
| "Linting clean" | Linter output showing 0 errors/warnings |

## Classify Before Claiming Done

Before marking a deliverable done, classify how it can be verified, then verify by that route:

| Class | Example | Verification route |
|-------|---------|-------------------|
| Diff-verifiable | new service, validation logic, migration file | the change appears in `git diff <base>...HEAD` and its check runs |
| Cross-repo | a file or contract in a sibling repository | the sibling is reachable on disk: check the path exists and holds the expected content; unreachable means unverifiable, cite what to check |
| External state | DNS record, cloud console setting, OAuth allowlist, secret-manager entry | unverifiable from the tree; name the system and the exact check the user must run |
| Content shape | a file must follow a convention | in this repo: run the project's validator; elsewhere: cross-repo rules apply |

The ledger tracks per-item sweep state; these outcomes classify each deliverable in the final report; a ledger row is `done` only when its deliverable classifies as done or changed. Outcomes are **done**, **partial**, **not done**, **changed** (same goal, different means; say how), or **unverifiable**. A concrete filesystem path is never unverifiable: run the existence check and report done or not done. Code that *handles* a deliverable is not the deliverable; shipping the extractor is not shipping the extracted file. When torn between done and unverifiable, report unverifiable; a confirmation prompt costs seconds, a silently missed deliverable does not.

**Every per-branch scope claim is falsifiable and needs its own evidence.** "Master-only" and "the stable branch still has the guard" are assertions a reviewer will check, and reading the broken code on the branch being patched proves nothing about the others. For each branch named, run both a containment query for the introducing commit and a direct read of the function body at that branch's tip. A branch can contain the commit and have been re-fixed since, or not contain it and be broken for another reason.

## When Verification Fails

If the output does not confirm the claim:

1. **Do not claim completion.** Report the actual failure output to the user.
2. **Do not retry the same verification** hoping for a different result.
3. **Return to implementation.** Fix the issue, then re-run from Step 1 of the Gate Function.
4. **Failure unrelated to the current changes** (pre-existing flaky test, environment issue)? State it explicitly with evidence: show the failure also occurs on the base branch or is a known issue. Pick that ref deliberately (the prior head is an intermediate state, so a regression claim is measured against the base the branch was cut from) and strip machinery the question does not need. Distrust a control that was expected to fail narrowly and came back with a wide sweep: a whole class may not have existed at that ref. "Environmental" and "pre-existing" are compatible, so naming one does not retire the other. Before either label, rule out the task's own formatters, hooks, and generators as the cause, including downstream failures they produced outside the approved files; an aggregate check that broke because this change triggered a regeneration is a regression of this change.

**Where the harness has a known noise floor, the signal is the failing-set diff, not the pass count.** Against a stubbed dependency or an unsupported lane, a suite reports the same fixed block of failures every run. Capture the failing test names on the unmodified base, re-run with the change, and diff the sets; an empty diff is the pass criterion.

## Pre-Commit Hook Failures

A failing pre-commit hook is a verification checkpoint, not an obstacle to route around. **`git commit --no-verify` is forbidden when the current session's changes caused the failure; fix the root cause.** Permitted only when: (1) the failure reproduces on the base branch (show it), and (2) the user saw the failure first. A `--no-verify` the user never saw is a defeated check, the same failure mode as claiming completion without evidence.

## Rationalization Prevention

Reasoning about the outcome instead of running the command means the Gate is not satisfied. "Should work", "trivial change", "just a refactor", "new tests pass" (not "all tests pass"), "CI will catch it": all the same failure mode, substituting confidence for evidence. Any satisfaction expression ("looks good", "seems correct", "that should do it") or any positive statement about completion, including paraphrases and synonyms, triggers the Gate: spirit over letter, rephrasing a claim to avoid the trigger words does not exempt it from verification.

## Completion Reporting

Report only facts that affect the handoff: the outcome, the command, URL, or click path that exercises it, failing or skipped checks, and any material residual risk. Include verification commands and observed results when the user cannot see them directly.

Do not emit empty status sections, concern slots, or scope ledgers to prove diligence. Name partial implementations, stubs, mocks, unreachable paths, and refusal-only behavior explicitly. When blocked, name the concrete blocker and the authority or information needed to continue.

## References

- [System-Wide Test Check](./system-wide-test-check.md): blast-radius verification for task completion (callbacks, integration, orphaned state)

## Integration

Referenced by `/ia-work` (before task completion, shipping, and merge/PR creation), `ia-receiving-code-review` (verify each fix before marking resolved), `ia-debugging` (before claiming a bug fixed), `ia-writing-tests` (tests as primary evidence), the `ia-design-iterator` and `ia-figma-design-sync` agents (verify rendering / Figma fidelity), and `/ia-verify` (full pre-PR verification pipeline).
