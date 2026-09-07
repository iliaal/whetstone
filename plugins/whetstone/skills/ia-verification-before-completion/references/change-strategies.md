# change strategies

## Verification Strategies by Change Type

For runnable code with those checks available, type-check and unit tests form a baseline, not sufficient proof on their own. Apply the repository's actual checks to other artifacts. Match the strategy to the change:

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
| Published package or release artifact | Install the published version into a throwaway directory and exercise the API the release added; the working tree shares the source, autoloader, and every uncommitted edit, so it proves nothing about what a consumer receives |
| Schema change | Old consumers parse the new shape (forward compat); new consumers handle old data still present (backward compat) |
| Documentation / prose | Read the rendered output; confirm links, formatting, and content match intent |
| Config with no validator | Validate syntax where possible (`jq .`, `yamllint`); otherwise read the file and confirm it matches the intended change |
| Non-runnable changes | `git diff`, confirm the diff matches intent, and state explicitly: "No automated verification available — verified by reading the diff." |

Reading code is not a strategy. If the table has no row for the change, fall back to the Non-runnable row. The principle holds even when no test suite applies: state what was checked and how.

A falling lint count is fully compatible with a corrupted file: most linters report only the *first* parse failure per file, so six broken literals surface as one error, six runs in a row, each looking like the last. A width-based rewriter has no parser -- it splits string literals into syntax errors and breaks comments mid-clause -- and a formatter run afterwards happily reformats prose that no longer says what the author wrote. In-place writes also replace a symlink with a regular file; check `git status --short` for a `T` (typechange) entry after any scripted edit.

**"Successfully rebased" is not proof the commit survived intact.** A three-way merge can resolve a pure insertion toward the new base when the surrounding lines were rewritten upstream -- no conflict, no warning, the hunk simply gone from the commit. After any rebase, cherry-pick, or history rewrite, diff the commit's touched-file list across the operation (`git show --stat --name-only HEAD@{1}` against `HEAD`) and confirm the expected content is still present. Do this whenever the base moved since the branch was cut, not only when conflicts appeared: a clean run is not the evidence. A second mechanism drops a hunk just as quietly: `.gitattributes` can bind a path to a merge driver that keeps one side (`driver = true`, `driver = touch %A`) and records a successful merge of a file it never merged, and during a rebase "ours" is the new base, so the incoming edit is the one discarded. Ask before the operation (`git check-attr merge -- <path>`, `git config --get merge.<name>.driver`); `git merge-file` does not consult `.gitattributes`.

**Self-review against the base, not HEAD.** `git diff` and `git diff HEAD` hide anything already committed on the branch. When HEAD holds an earlier attempt at the same fix, the superseded code is part of the base and never appears as an add or a remove -- the patch is unreviewable that way, and layering a second approach on top of a half-reverted first one is how a double-free or double-write ships. Diff against the upstream branch (`git diff origin/<branch> -- <files>`) and re-read the whole changed region, including lines believed reverted.

## Adversarial Probes

For any change that touches production logic, include at least one adversarial probe in the verification. Pick the most relevant from:

- **Boundary value**: 0, -1, empty string, empty array, `null`, `undefined`, `MAX_INT`, 1-char unicode combining mark
- **Concurrency**: two parallel requests with the same identifier (for state changes, races, double-spend classes)
- **Idempotency**: run the same mutation twice; the second should either no-op or error cleanly, not corrupt state
- **Orphan op**: delete/update/get a nonexistent ID — does it 404/return-null as expected, or throw an internal error?
- **Implementation shape**: vary what callers supply to an I/O path or an extension point -- a plugin with and without each optional method, a destination that exists and one that does not, a symlink, a read-only parent. A green suite, a clean sanitizer, and a differential API sweep share one blind spot: the signature is unchanged while the capability is gone, because an identical `false` for a different reason reads as no change. State the capability verified, not the aggregate.

Exempt: docs changes, trivial typo fixes, pure rename refactors. Everything else: one probe minimum -- a report with zero adversarial probes is a happy-path confirmation, not verification.

**A corpus assembled to expose a defect cannot test the fix.** Every row is an instance of the defect, so green proves only that the known cases are closed; the cases a fix can break are the ones the corpus omits, and it has a hole in exactly the region the defect reached through. Build a second set from cases the base already handles correctly, assert that none of them regresses, and state both numbers. If every row is a case the claim names, the measurement is of the claim, not of the code. When an author reports a wider run, check whether they varied a new dimension or only scaled yours.

## Review Staleness

Before shipping, check whether prior reviews (agent or human) are still valid. If commits landed after the last review (`git log --oneline <review-commit>..HEAD`), verify the new changes don't invalidate its conclusions: previously flagged issues are still fixed, and no new code contradicts the review's approval.

**Refresh the source of truth before concluding from what it does not contain.** A snapshot fetched minutes ago supports "I did not see X", never "X does not exist" -- and a stale snapshot can *manufacture* a finding rather than merely miss one. Re-fetch immediately before the decision, not only before acting on it, whenever the conclusion depends on nothing having happened: unpushed local commits, a queued job, an unsynced remote all read as absence. Line numbers, anchors, and citations computed against the old state need re-deriving too; a moved base invalidates every coordinate even when the substance survives. Conclusions about a *person's* actions do not fail safe -- hold those to a fresh fetch and a second corroborating signal before they go anywhere external.
