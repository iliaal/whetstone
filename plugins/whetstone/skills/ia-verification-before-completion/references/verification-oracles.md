# verification oracles

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

**A command that cannot return a positive has not returned a negative.** A pathspec the tool globs differently than you read it, a filter that discards `command not found`, a wrapper exiting 0 on an empty stream -- each yields a clean zero that supports whatever is being tested. Run a positive control through the *same* invocation shape (same tool, ref, filter, shell) and read its output before you read the zero. Never filter stderr on the run that establishes the harness works.

**An absent output artifact is a launch failure, never an empty result.** When a wrapper writes its findings to a file, a run that never started and a run that found nothing both give exit 0 and no file. Require the artifact to exist before interpreting it.

**A reconciling total is not per-item agreement.** Counts, sums, and digests all pass when two items' verdicts are swapped, and two independent errors pointing opposite ways cancel into a *correct* aggregate. Make one typed per-item record the authority, cross-check every id against the producer that knows them, and derive summaries from that record; test with a two-row permutation whose totals do not move. For an evidence block you assemble yourself, write down the relation the counts satisfy by construction (baseline + added = total) and evaluate that instead of re-running -- a re-run reproduces the same reading.

**Prove which binary produced the evidence.** A green run says nothing about *what ran*. PATH lookup, a stale installed copy, a compiled sibling, or a system interpreter can shadow the tree under test: run `command -v`, resolve symlinks, and compare the reported version or build SHA against the source being verified. For deployed code, run the check through the exact interpreter or entry point the service uses -- the one named in the scheduler entry, the unit's `ExecStart`, or the image's `CMD` -- never the bare binary on PATH. An error about a symbol or argument the deployed code plainly uses is a tell that the check is on the wrong interpreter, not that the deploy is broken. A live failure from an installed helper does not refute a source fix until that identity is checked.

**When the subject is a tree materialized at a revision, prove the bytes before trusting the result.** Extracting a subtree at a commit can half-fail and leave what was there before. Diff one file under test against its content at that revision, or compare hashes, as a provenance control -- the same check catches a run against the working tree that was believed pinned.

**Project-declared gates.** Before a push or PR open, read `CLAUDE.md`, `AGENTS.md`, and `CONTRIBUTING.md` if not already loaded. For each declared check, identify its triggering action, scope conditions, order, and blocking or warning status. Run every check applicable to the current action in the required order; stop on the first unmet blocking gate and name it verbatim from the instruction file. Report warning-only failures without promoting them to blockers. A release-only metadata, changelog, or validation requirement applies during release, not an ordinary push or PR. Do not invent gates, widen their triggers, or skip an applicable requirement.
