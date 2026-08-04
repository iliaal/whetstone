---
name: ia-verification-before-completion
class: discipline
description: >-
  Enforces fresh verification evidence before any completion claim. Use when
  about to claim "tests pass", "bug fixed", "done", "ready to merge", handing
  off work, or before editing when a request has ambiguous scope.
---

# Verification Before Completion

## The Rule

No completion claims without fresh verification evidence. If the verification command has not been run **immediately before the claim**, the claim cannot be made.

"Should pass", "probably works", and "looks correct" are not verification. Only command output confirming the claim counts (typically exit code 0). Pre-existing failures causing non-zero exits unrelated to the current changes: see "When Verification Fails" below.

## Pre-Verification Check

Before running verification, check the working tree state: `git status --porcelain`. If there are uncommitted changes unrelated to the current task, handle them first (commit, stash, or acknowledge) -- verification commits on top of a dirty tree create tangled history.

**Dirty tree + shared-module change → local green is not evidence.** Reproduce on a clean base ([isolated-verification.md](./references/isolated-verification.md)).

**Broad-blast-radius changes need the baseline captured before the first write.** For a dependency bump, framework upgrade, codegen change, or migration, run the repo's validation suite against the existing state first and record the exact command set. Rerun that same set verbatim afterward -- a post-change run of a *different* command set proves nothing. If the baseline is already red, stop and report before writing anything: starting a migration on a red base makes every later failure unattributable, and a recorded red baseline is one step from "it was already broken, not my problem". This is the one case where the retroactive base-branch proof under When Verification Fails is impractical -- a regenerated lockfile does not `git stash` cleanly. Ordinary source edits stay on that retroactive path.

For delegated work: never trust the implementer subagent's own report -- spec compliance and quality are separate concerns, verify both. Confirm via the VCS diff that changes were actually made, then run the verification command directly; never relay the subagent's claim.

## Scope Confirmation (Pre-Edit Gate)

This gate fires at task start, before the first edit. When a request uses ambiguous spatial scope -- "migrate my project", "refactor the codebase", "update everywhere", "fix this across the app", "my code/repo/project" -- confirm the concrete scope before any Write or Edit. Imperative phrasing is not defined scope.

Run a breakdown command to surface the real blast radius:

```bash
rg -l 'pattern' | cut -d/ -f1 | sort | uniq -c | sort -rn   # files per top-level dir
rg -l 'pattern' | xargs dirname | sort -u                   # affected directories
```

Present the result -- "This touches N files across M subsystems" -- with scope options: (a) everything, (b) just <subset>, (c) pick specific files. Ask via AskUserQuestion (Claude Code; load with ToolSearch `select:AskUserQuestion` if not loaded) or request_user_input (Codex); fall back to numbered options in chat. Do not start editing until the user commits to one option.

**When this applies**: any request whose scope could plausibly span more than one directory AND where the user has not enumerated files. For a request with explicit file paths, skip this gate.

## Sweep Completion

For tasks whose scope is *every* item in a set -- a repo-wide rename, "migrate everywhere", audit every file, resolve all findings -- the Gate Function proves a command passed, not that it ran over the whole set. Track coverage explicitly.

Enumerate the set into a ledger held outside version control -- a session-scratch path where the harness provides one, otherwise any git-ignored local directory, never a tracked file -- one row per item with an explicit disposition: `pending`, `done`, `excluded (reason)`, or `blocked (evidence)`. Completion requires zero `pending` and zero `blocked` -- "I covered a lot of them" is not a disposition.

Two rules close the holes that make a ledger lie:
- Re-enumerate after any path move or rename, so items created or relocated mid-sweep enter coverage instead of falling outside the original list.
- Keep removed items in the ledger until explicitly accounted for -- an item that silently disappears reads identically to one that was finished.

Never claim coverage the ledger does not show.

## Gate Function

Before any success claim, run through these five steps:

| Step | Action | Example |
|------|--------|---------|
| **1. Identify** | What command proves this claim? The full chain -- build -> typecheck -> lint -> test -> security scan -> diff review, **stop on first failure** -- applies to ship-level claims (commit/push/PR-ready); for a single claim, run the proof command from the Common Claims table below. | `pytest tests/`, `npm test`, `curl -s localhost:3000/health` |
| **2. Run** | **Run it now, in this same message.** Output from an earlier turn is stale and does not count. | "I ran it earlier" fails this step |
| **3. Read** | Read the complete output, check exit code | Don't scan for "passed" -- read failure counts, warnings, errors |
| **4. Verify** | Does the output actually confirm the claim? | "42 passed, 0 failed" confirms "tests pass". "41 passed, 1 failed" does not. |
| **5. Claim** | Only now make the statement | "All 42 tests pass" with the evidence visible |

## Verification Strategies by Change Type

Type-check and unit tests are the universal baseline — not sufficient proof on their own. Match the strategy to the change:

| Change type | Required verification |
|-------------|----------------------|
| Frontend (component, page, form) | Start the dev server, exercise the feature in a browser, check the console; test the happy path AND one failure path |
| Backend handler / endpoint | `curl` the endpoint, check response shape and status code, hit at least one error path (invalid input, missing auth) |
| CLI tool | Run the binary with real inputs; check stdout, stderr, exit code. Run from `/tmp` to catch "only works from source" bugs |
| Infra / IaC (Terraform, Dockerfile, k8s) | `terraform plan` / `docker build` / `kubectl apply --dry-run=server`; review the diff before applying |
| Database migration | Run migration up, down, then up again against production-shape data |
| Refactoring (no behavior change) | Full test suite passes unchanged; public API surface diff shows no breakage (`grep` exported identifiers) |
| Library / package update | Run the consumer's test suite against the new version; check for deprecation warnings |
| Schema change | Old consumers parse the new shape (forward compat); new consumers handle old data still present (backward compat) |
| Documentation / prose | Read the rendered output; confirm links, formatting, and content match intent |
| Config with no validator | Validate syntax where possible (`jq .`, `yamllint`); otherwise read the file and confirm it matches the intended change |
| Non-runnable changes | `git diff`, confirm the diff matches intent, and state explicitly: "No automated verification available — verified by reading the diff." |

Reading code is not a strategy. If the table has no row for the change, fall back to the Non-runnable row. The principle holds even when no test suite applies: state what was checked and how.

## Adversarial Probes

For any change that touches production logic, include at least one adversarial probe in the verification. Pick the most relevant from:

- **Boundary value**: 0, -1, empty string, empty array, `null`, `undefined`, `MAX_INT`, 1-char unicode combining mark
- **Concurrency**: two parallel requests with the same identifier (for state changes, races, double-spend classes)
- **Idempotency**: run the same mutation twice; the second should either no-op or error cleanly, not corrupt state
- **Orphan op**: delete/update/get a nonexistent ID — does it 404/return-null as expected, or throw an internal error?

Exempt: docs changes, trivial typo fixes, pure rename refactors. Everything else: one probe minimum -- a report with zero adversarial probes is a happy-path confirmation, not verification.

## Review Staleness

Before shipping, check whether prior reviews (agent or human) are still valid. If commits landed after the last review (`git log --oneline <review-commit>..HEAD`), verify the new changes don't invalidate its conclusions: previously flagged issues are still fixed, and no new code contradicts the review's approval.

## When This Applies

- About to claim "tests pass", "build succeeds", or "bug fixed"
- About to commit, push, create a PR, or mark a task complete
- After completing each plan step / before starting the next file
- Reporting results to the user
- A subagent reports success on delegated work

## Red Flags

**Fantasy assessment auto-fail.** "Zero issues found" on a first implementation pass is a red flag, not a green light -- first implementations typically need 2-3 revision cycles, so "perfect on the first try" more likely means incomplete verification. Re-verify with a broader scope.

**Negative confirmation at signoff.** State what defect classes were checked and NOT found, not just what passed: "tests pass, no type errors, no lint warnings, no security flags in the changed files" proves the scope of verification; "tests pass" alone does not.

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

## When Verification Fails

If the output does not confirm the claim:

1. **Do not claim completion.** Report the actual failure output to the user.
2. **Do not retry the same verification** hoping for a different result.
3. **Return to implementation.** Fix the issue, then re-run from Step 1 of the Gate Function.
4. **Failure unrelated to the current changes** (pre-existing flaky test, environment issue)? State it explicitly with evidence: show the failure also occurs on the base branch or is a known issue.

## Pre-Commit Hook Failures

A failing pre-commit hook is a verification checkpoint, not an obstacle to route around. **`git commit --no-verify` is forbidden when the current session's changes caused the failure -- fix the root cause.** Permitted only when: (1) the failure reproduces on the base branch (show it), and (2) the user saw the failure first. A `--no-verify` the user never saw is a defeated check -- the same failure mode as claiming completion without evidence.

## Rationalization Prevention

Reasoning about the outcome instead of running the command means the Gate is not satisfied. "Should work", "trivial change", "just a refactor", "new tests pass" (not "all tests pass"), "CI will catch it" -- all the same failure mode: substituting confidence for evidence. Any satisfaction expression ("looks good", "seems correct", "that should do it") or any positive statement about completion -- including paraphrases and synonyms -- triggers the Gate: spirit over letter, rephrasing a claim to avoid the trigger words does not exempt it from verification.

## Completion Report Format

After verification passes, produce a structured report rather than an open-ended summary:

```
## Completion report

**Status**: DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT

**Changes made**
- path/to/file.ts: [one-line description of what changed and why]
- path/to/other.ts: [one-line description]

**Next**
- [the one command to paste, URL to open, or click-path that exercises this in one step -- or the decision now owed]

**Things I didn't touch (intentionally)**
- [thing noticed but out of scope, with one-line reason]
- [adjacent issue deferred, with one-line reason]

**Potential concerns**
- [any risk, uncertainty, or open question the reviewer should know about]
- [or "none"]

**Verification evidence**
- [command]: [exit code / result summary]
```

DONE_WITH_CONCERNS makes the `Potential concerns` section mandatory; BLOCKED and NEEDS_CONTEXT must name the blocker or the missing information. The `Things I didn't touch` section is not optional -- if nothing was noticed, write "nothing noticed"; the goal is to prove scope was considered, not to pad the report.

`Next` is one line, and it is not a summary of what changed -- it is the thing the reader does now. It is usually *not* the verification command: `pytest tests/test_auth.py` proves the work happened, `npm run dev` then open `/settings` exercises it. When the result is not directly exercisable (docs, config, refactor), say so and name what was read or checked instead. When work is blocked or awaiting a decision, `Next` names the decision, not the blocker.

## References

- [System-Wide Test Check](./references/system-wide-test-check.md) -- blast-radius verification for task completion (callbacks, integration, orphaned state)

## Integration

Referenced by `/ia-work` (before task completion, shipping, and merge/PR creation), `ia-receiving-code-review` (verify each fix before marking resolved), `ia-debugging` (before claiming a bug fixed), `ia-writing-tests` (tests as primary evidence), the `ia-design-iterator` and `ia-figma-design-sync` agents (verify rendering / Figma fidelity), and `/ia-verify` (full pre-PR verification pipeline).
