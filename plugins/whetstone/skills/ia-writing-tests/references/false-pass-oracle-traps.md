# False-Pass Oracle Traps

Assertion oracles that can report success without observing failure, moved from the SKILL.md Anti-Patterns section.

## Piping a command into `grep -q` to assert on its output

**Symptom:** the assertion reports "absent" for a string plainly present in a manual run. Under `set -o pipefail` the pipeline's status is the *writer's*: `grep -q` exits on first match and closes the pipe, so the producer dies of SIGPIPE and the pipeline fails **because the assertion matched**. Independently, a command that legitimately exits non-zero (a refusal path, a status code that is part of the contract) fails the pipeline regardless of the match. Either way the false negative reads as a behavioral finding and sends you into the production code.

**Fix:** capture, then match. `out=$(cmd 2>&1)` on one line, `grep -q 'needle' <<<"$out"` on the next; never put the command and the matcher in one pipeline. Two adjacent shapes to avoid in assertions: `grep -c` prints `0` *and* exits 1, so `grep -c p f || printf 0` emits `0\n0`; and `cmd && x || y` is not if-then-else: `y` also runs when `x` fails.

## A comparison oracle that fails open

**Symptom:** the harness compares two producers with `diff -q <(producer_a | filter) <(producer_b | filter)`. `diff` observes the streams, not whether either producer succeeded: two failed producers yield two empty streams and compare equal. Comparing only added lines has the same hole: two deletions of *different* content both produce an empty `^+` stream, and identical file and line counts do not mean identical content.

**Fix:** capture each producer to a temporary file and check its exit status before comparing. Compare both added and removed hunk bodies from a zero-context diff, not summaries or diffstats. Classify a producer failure, a binary or metadata-only patch, or a comparison I/O error as *undecidable*, never as *identical*.

## A green suite over a feature the test environment disables

**Symptom:** The code path that would fail is behind a config or environment flag that defaults off, and the test environment sets no override. Every test exercising the affected object passes, including tests written for it, and the failure appears on the first write in an environment where the flag is on. Grepping the repository reinforces the wrong conclusion, because the enabled value lives in deployment configuration (a task definition, a parameter store), not in the codebase; the only value in the tree is the `false` default.

**Fix:** Before reading a pass as coverage, check whether the flag gating the consumer that would fail is on under test. Re-run one existing test with the flag forced on, alongside a test touching only unaffected objects as a control, so a failure is attributable to the flag rather than to the environment change. When the disabling guard keys on the test runner itself (an environment variable the runner sets), no in-suite test can observe the behavior at all. Verify that surface out of band with a standalone process using production configuration and a capturing transport, and treat every in-suite assertion about it as vacuous until one has been shown able to fail.

## An expected-output pattern that ends in a bare wildcard

**Symptom:** the expectation matches the run's real output, and then a trailing wildcard absorbs whatever the harness appends after an abnormal exit. A run that prints the expected line and immediately crashes passes.

**Fix:** anchor the expectation to the real last line. Plant the failure (kill the process after the matched line) and confirm that expectation fails. Prefer a greedy wildcard to a lazy one before an end anchor: a lazy quantifier can exhaust the engine's backtrack budget, and most engines report that exhaustion as an error the harness reads as "no match".

## A conformance harness that normalizes before comparing

**Symptom:** the spec suite compares through a normalizer that ignores insignificant formatting, so a defect living inside that class passes identically with and without the bug. "652/652 against the spec" is a claim about the normalized form, not about bytes.

**Fix:** assert against the spec's literal output wherever consumers care about bytes. When a byte-exact test disagrees with an upstream green suite, suspect the normalizer before suspecting the test.

## Gating a test lane on a grep of the runner's summary

**Symptom:** `runner | tee out; grep -q '^Tests failed *: [1-9]' out` goes green when the runner colorizes its output and the anchor never matches, and again when the runner crashes before printing a summary at all. `rc=$?` after the pipe is `tee`'s status, not the runner's.

**Fix:** read `${PIPESTATUS[0]}` and gate on it. Corollary: a historically green lane is not evidence the suite passed, so a tightening fix that turns a lane red is evidence the old gate was masking.

## A readiness predicate whose alternation admits a mid-stream match

**Symptom:** a background producer is waited on with a condition that ORs the real completion marker against something cheap: `until [ -s "$OUT" ] && grep -qiE 'done marker|^\s*$' "$OUT"; do sleep 15; done`. The `^\s*$` branch matches the first blank line, which the producer emits before it answers anything, so the wait reports ready on poll #1. The half-written artifact then reads as a *wrong answer* rather than a visibly incomplete one: a tail lands in the middle of the producer's own echoed input, which files as a defect report about the tool when the truth was a read that landed a few kilobytes short of the end of the write. Nothing about the output's appearance separates the two.

**Fix:** match a marker that cannot appear mid-stream (the final result block, never a whitespace pattern and never a token the stream can print more than once) and confirm the producer has exited before reading anything it wrote. A tail is evidence about the file; only the process table is evidence about completion. Prefer the harness's own completion signal to a hand-rolled poll, since the hand-rolled loop is what gets reached for when the wait has to happen inside one turn, and that is exactly when the predicate goes sloppy.

## A GNU-only matcher inside a cross-OS assertion

**Symptom:** `grep -qP` as an `if` condition fails open on BSD grep: there is no `-P`, exit 2 reads as "pattern absent", and the check passes. The same gap points the other way in a summary parser: `grep -oP` errors, the parsed count defaults to zero, and the "suite not effective" branch fires on a green suite.

**Fix:** parse with POSIX awk, and gate on exit status before interpreting any text.

## An oracle newer than the supported floor

**Symptom:** the API under test is version-gated, but the helper the test calls to compute the expected answer is not. The suite is green on the development version, and that green gets read as "supported across the range". On the oldest supported build the file fails to load, so the case never runs and never reports, or reports a load error nobody traces back to the oracle.

**Fix:** express the oracle in the oldest supported dialect, and run any new test once against a floor build before pushing.

## A smoke input that does not exercise a budget

**Symptom:** a trivial payload passes under a size, time, or token limit that production-shaped input exhausts, so the limit is never reached and the green run gets read as capacity.

**Fix:** probe with input of the real shape and size against the real limit, and parse the result rather than the exit status; a truncation signal alongside empty content is the signature.

## Retiring a test suite on a similar test count

**Symptom:** a suite is rewritten in another runner and the migration is declared done because the counts match. Parameterized cases collapse many legacy assertions, and a translated expectation can faithfully repeat its source's mistake.

**Fix:** keep the old suite frozen as an independent oracle until four gates pass: every legacy assertion or named section maps to a collected replacement contract; both suites run against the same built artifacts and are compared on exit codes, raw bytes, file modes, and artifacts rather than summaries; focused mutations of fail-closed boundaries make *both* suites fail on the intended assertion and go green again after cleanup; and the replacement passes serially, concurrently, and in randomized order. Never change a product expectation while translating it; record the discovered defect separately and land its regression with the product fix.
