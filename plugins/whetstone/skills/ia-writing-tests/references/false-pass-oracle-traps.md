# False-Pass Oracle Traps

Assertion oracles that can report success without observing failure, moved from the SKILL.md Anti-Patterns section.

## Piping a command into `grep -q` to assert on its output

**Symptom:** the assertion reports "absent" for a string plainly present in a manual run. Under `set -o pipefail` the pipeline's status is the *writer's*: `grep -q` exits on first match and closes the pipe, so the producer dies of SIGPIPE and the pipeline fails **because the assertion matched**. Independently, a command that legitimately exits non-zero -- a refusal path, a status code that is part of the contract -- fails the pipeline regardless of the match. Either way the false negative reads as a behavioral finding and sends you into the production code.

**Fix:** capture, then match. `out=$(cmd 2>&1)` on one line, `grep -q 'needle' <<<"$out"` on the next; never put the command and the matcher in one pipeline. Two adjacent shapes to avoid in assertions: `grep -c` prints `0` *and* exits 1, so `grep -c p f || printf 0` emits `0\n0`; and `cmd && x || y` is not if-then-else -- `y` also runs when `x` fails.

## A comparison oracle that fails open

**Symptom:** the harness compares two producers with `diff -q <(producer_a | filter) <(producer_b | filter)`. `diff` observes the streams, not whether either producer succeeded -- two failed producers yield two empty streams and compare equal. Comparing only added lines has the same hole: two deletions of *different* content both produce an empty `^+` stream, and identical file and line counts do not mean identical content.

**Fix:** capture each producer to a temporary file and check its exit status before comparing. Compare both added and removed hunk bodies from a zero-context diff, not summaries or diffstats. Classify a producer failure, a binary or metadata-only patch, or a comparison I/O error as *undecidable*, never as *identical*.

## A green suite over a feature the test environment disables

**Symptom:** The code path that would fail is behind a config or environment flag that defaults off, and the test environment sets no override. Every test exercising the affected object passes, including tests written for it, and the failure appears on the first write in an environment where the flag is on. Grepping the repository reinforces the wrong conclusion, because the enabled value lives in deployment configuration (a task definition, a parameter store), not in the codebase -- the only value in the tree is the `false` default.

**Fix:** Before reading a pass as coverage, check whether the flag gating the consumer that would fail is on under test. Re-run one existing test with the flag forced on, alongside a test touching only unaffected objects as a control, so a failure is attributable to the flag rather than to the environment change.

## Retiring a test suite on a similar test count

**Symptom:** a suite is rewritten in another runner and the migration is declared done because the counts match. Parameterized cases collapse many legacy assertions, and a translated expectation can faithfully repeat its source's mistake.

**Fix:** keep the old suite frozen as an independent oracle until four gates pass: every legacy assertion or named section maps to a collected replacement contract; both suites run against the same built artifacts and are compared on exit codes, raw bytes, file modes, and artifacts rather than summaries; focused mutations of fail-closed boundaries make *both* suites fail on the intended assertion and go green again after cleanup; and the replacement passes serially, concurrently, and in randomized order. Never change a product expectation while translating it -- record the discovered defect separately and land its regression with the product fix.
