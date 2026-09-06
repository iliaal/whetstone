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

Evidence is invalid when the change makes the oracle easier to satisfy instead of making the behavior correct. Never weaken a specification, assertion, test, validator, or acceptance criterion to obtain a pass. Regenerate expected output only after reviewing and justifying the semantic change. Do not hard-code the exercised subject or success path.

Classify proof honestly. Fixtures, mocks, seeded rows, retained captures, and recorded responses can support deterministic tests, but they are not live evidence. Claim live behavior only after a fresh process exercises the intended entry point against runtime-selected or independently varied subjects where that distinction matters.

**Tightening validation on input you cannot read is not covered by green tests.** When a change moves a parser from lenient to strict (`validate=True`, `strict=True`, `errors="strict"`, a tight regex replacing a permissive built-in) and the value comes from a secret store, an environment variable, or a human, the tests construct their input with the canonical encoder and are green by construction -- they cannot emit the stray byte the old leniency was absorbing. "It has worked in production for a year" is likewise zero evidence: the leniency is precisely what hid the byte. Pair the strictness with an explicit normalization step and state the coverage gap rather than reporting the change as verified.

When the positive capability is safe, authorized, and in scope, a refusal-only path is incomplete. Verify and report the refusal behavior, but do not close the feature until the positive path works through its intended entry point.

## Pre-Verification Check

Before running verification, check the working tree state: `git status --porcelain`. If there are uncommitted changes unrelated to the current task, handle them first (commit, stash, or acknowledge) -- verification commits on top of a dirty tree create tangled history.

**Dirty tree + shared-module change → local green is not evidence.** Reproduce on a clean base ([isolated-verification.md](./references/isolated-verification.md)).

**Broad-blast-radius changes need the baseline captured before the first write.** For a dependency bump, framework upgrade, codegen change, or migration, run the repo's validation suite against the existing state first and record the exact command set. Rerun that same set verbatim afterward -- a post-change run of a *different* command set proves nothing. If the baseline is already red, stop and report before writing anything: starting a migration on a red base makes every later failure unattributable, and a recorded red baseline is one step from "it was already broken, not my problem". This is the one case where the retroactive base-branch proof under When Verification Fails is impractical -- a regenerated lockfile does not `git stash` cleanly. Ordinary source edits stay on that retroactive path.

For delegated work: never trust the implementer subagent's own report -- spec compliance and quality are separate concerns, verify both. Confirm via the VCS diff that changes were actually made, then run the verification command directly; never relay the subagent's claim.

## Scope Confirmation (Pre-Edit Gate)

This gate fires at task start, before the first edit. When a request uses ambiguous spatial scope -- "migrate my project", "refactor the codebase", "update everywhere", "fix this across the app", "my code/repo/project" -- inspect the repository to resolve the concrete scope before any Write or Edit. Imperative phrasing is not defined scope.

Run a breakdown command to surface the real blast radius:

```bash
rg -l 'pattern' | cut -d/ -f1 | sort | uniq -c | sort -rn   # files per top-level dir
rg -l 'pattern' | xargs dirname | sort -u                   # affected directories
```

When the request and repository structure identify one safe interpretation, state the assumption and proceed. If multiple interpretations materially change the result, present the breakdown and ask via AskUserQuestion (Claude Code; load with ToolSearch `select:AskUserQuestion` if not loaded) or request_user_input (Codex); fall back to numbered options in chat. Do not start editing until that material choice is resolved.

**When this applies**: any request whose scope could plausibly span more than one subsystem and cannot be resolved safely from the request and repository structure. For a request with explicit file paths or one clear repository-wide interpretation, skip the question.

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

**A suite that executed nothing exits 0.** Zero failures is not a pass when the executed count is also zero -- an unloadable module, an unmet skip condition, a collection error, or a filter matching no tests all produce a green exit and an empty summary. Read the executed and passed counts, not just the failure count, and require the passed count to be positive before accepting a run as evidence. Where a suite can legitimately skip everything (optional dependency, service-backed cases), keep at least one unconditional case so a positive count still means something.

**Prove which binary produced the evidence.** A green run says nothing about *what ran*. PATH lookup, a stale installed copy, a compiled sibling, or a system interpreter can shadow the tree under test: run `command -v`, resolve symlinks, and compare the reported version or build SHA against the source being verified. For deployed code, run the check through the exact interpreter or entry point the service uses -- the one named in the scheduler entry, the unit's `ExecStart`, or the image's `CMD` -- never the bare binary on PATH. An error about a symbol or argument the deployed code plainly uses is a tell that the check is on the wrong interpreter, not that the deploy is broken. A live failure from an installed helper does not refute a source fix until that identity is checked.

**Project-declared gates.** Before any push or PR open, read `CLAUDE.md`, `AGENTS.md`, and `CONTRIBUTING.md` if not already loaded, and extract any declared pre-push or review-ready requirement -- a metadata or drift `--check` script, a changelog-entry rule, a required lint or test target, or a release-gate list. Run each one found, in order, and stop on the first unmet gate, naming it verbatim from the instruction file. Do not invent a gate the instructions don't state, and do not skip one that is stated.

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
| Mechanical or scripted sweep (width-based rewrap, regex pass, in-place edit) | Verify with a parser or compiler (`compileall`, `cargo check`, `tsc --noEmit`, a build), never with the linter's error tally |
| Library / package update | Run the consumer's test suite against the new version; check for deprecation warnings |
| Schema change | Old consumers parse the new shape (forward compat); new consumers handle old data still present (backward compat) |
| Documentation / prose | Read the rendered output; confirm links, formatting, and content match intent |
| Config with no validator | Validate syntax where possible (`jq .`, `yamllint`); otherwise read the file and confirm it matches the intended change |
| Non-runnable changes | `git diff`, confirm the diff matches intent, and state explicitly: "No automated verification available — verified by reading the diff." |

Reading code is not a strategy. If the table has no row for the change, fall back to the Non-runnable row. The principle holds even when no test suite applies: state what was checked and how.

A falling lint count is fully compatible with a corrupted file: most linters report only the *first* parse failure per file, so six broken literals surface as one error, six runs in a row, each looking like the last. A width-based rewriter has no parser -- it splits string literals into syntax errors and breaks comments mid-clause -- and a formatter run afterwards happily reformats prose that no longer says what the author wrote. In-place writes also replace a symlink with a regular file; check `git status --short` for a `T` (typechange) entry after any scripted edit.

**"Successfully rebased" is not proof the commit survived intact.** A three-way merge can resolve a pure insertion toward the new base when the surrounding lines were rewritten upstream -- no conflict, no warning, the hunk simply gone from the commit. After any rebase, cherry-pick, or history rewrite, diff the commit's touched-file list across the operation (`git show --stat --name-only HEAD@{1}` against `HEAD`) and confirm the expected content is still present. Do this whenever the base moved since the branch was cut, not only when conflicts appeared: a clean run is not the evidence.

**Self-review against the base, not HEAD.** `git diff` and `git diff HEAD` hide anything already committed on the branch. When HEAD holds an earlier attempt at the same fix, the superseded code is part of the base and never appears as an add or a remove -- the patch is unreviewable that way, and layering a second approach on top of a half-reverted first one is how a double-free or double-write ships. Diff against the upstream branch (`git diff origin/<branch> -- <files>`) and re-read the whole changed region, including lines believed reverted.

## Adversarial Probes

For any change that touches production logic, include at least one adversarial probe in the verification. Pick the most relevant from:

- **Boundary value**: 0, -1, empty string, empty array, `null`, `undefined`, `MAX_INT`, 1-char unicode combining mark
- **Concurrency**: two parallel requests with the same identifier (for state changes, races, double-spend classes)
- **Idempotency**: run the same mutation twice; the second should either no-op or error cleanly, not corrupt state
- **Orphan op**: delete/update/get a nonexistent ID — does it 404/return-null as expected, or throw an internal error?

Exempt: docs changes, trivial typo fixes, pure rename refactors. Everything else: one probe minimum -- a report with zero adversarial probes is a happy-path confirmation, not verification.

## Review Staleness

Before shipping, check whether prior reviews (agent or human) are still valid. If commits landed after the last review (`git log --oneline <review-commit>..HEAD`), verify the new changes don't invalidate its conclusions: previously flagged issues are still fixed, and no new code contradicts the review's approval.

**Refresh the source of truth before concluding from what it does not contain.** A snapshot fetched minutes ago supports "I did not see X", never "X does not exist" -- and a stale snapshot can *manufacture* a finding rather than merely miss one. Re-fetch immediately before the decision, not only before acting on it, whenever the conclusion depends on nothing having happened: unpushed local commits, a queued job, an unsynced remote all read as absence. Line numbers, anchors, and citations computed against the old state need re-deriving too; a moved base invalidates every coordinate even when the substance survives. Conclusions about a *person's* actions do not fail safe -- hold those to a fresh fetch and a second corroborating signal before they go anywhere external.

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

The ledger tracks per-item sweep state; these outcomes classify each deliverable in the final report; a ledger row is `done` only when its deliverable classifies as done or changed. Outcomes are **done**, **partial**, **not done**, **changed** (same goal, different means -- say how), or **unverifiable**. A concrete filesystem path is never unverifiable: run the existence check and report done or not done. Code that *handles* a deliverable is not the deliverable -- shipping the extractor is not shipping the extracted file. When torn between done and unverifiable, report unverifiable; a confirmation prompt costs seconds, a silently missed deliverable does not.

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

## Completion Reporting

Report only facts that affect the handoff: the outcome, the command, URL, or click path that exercises it, failing or skipped checks, and any material residual risk. Include verification commands and observed results when the user cannot see them directly.

Do not emit empty status sections, concern slots, or scope ledgers to prove diligence. Name partial implementations, stubs, mocks, unreachable paths, and refusal-only behavior explicitly. When blocked, name the concrete blocker and the authority or information needed to continue.

## References

- [System-Wide Test Check](./references/system-wide-test-check.md) -- blast-radius verification for task completion (callbacks, integration, orphaned state)

## Integration

Referenced by `/ia-work` (before task completion, shipping, and merge/PR creation), `ia-receiving-code-review` (verify each fix before marking resolved), `ia-debugging` (before claiming a bug fixed), `ia-writing-tests` (tests as primary evidence), the `ia-design-iterator` and `ia-figma-design-sync` agents (verify rendering / Figma fidelity), and `/ia-verify` (full pre-PR verification pipeline).
