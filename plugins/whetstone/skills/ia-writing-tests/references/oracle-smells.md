# oracle smells

### An aggregate assertion that names no offender

**Symptom:** `assert all(r.returncode == 0 for r in results)` renders as a bare `assert False`. The failure names neither the failing item nor its message, so diagnosing it costs an extra cycle re-running under a patched assertion.

**Fix:** collect the offenders and assert on the list -- `assert [r for r in results if r.returncode != 0] == []` -- so the output carries identity and error text. Same rule for regression pins: pin the specific offending names, not a count. A defect of this class re-enters as a different plausible-looking value, and a count notices nothing.

### Persistent test infrastructure state contamination

**Symptom:** Integration tests fail with row-count multipliers (expected 2 rows, got 8) yet pass on a fresh container -- persistent infrastructure kept state from prior runs. **Diagnostic shortcut:** a clean integer multiple (2x, 3x, 4x...) between expected and actual means state contamination, not a logic bug -- logic bugs rarely produce uniform multipliers across unrelated assertions.

**Fix:** Reset infrastructure state between runs -- ephemeral containers, fixture `TRUNCATE`, or volume teardown (ladder in the reference); never rely on tests "cleaning up after themselves."

Isolation and sandbox traps -- containerized-timeout leaks, a harness sandboxing the subject in the primitive under test, global before/after snapshots, relocated environment variables, assertions pinned to stream chunking, an out-of-memory kill that prints no failure summary, and stub fixtures that quietly become allowlists -- are in [isolation-and-sandbox-traps.md](./isolation-and-sandbox-traps.md).

### Vacuous forall over an empty collection

**Symptom:** A `forall`-style assertion (`every`, `all`, `.iter().all()`) passes vacuously -- the factory never attached children, and every such operator returns `true` over an empty collection.

**Fix:** Attach a realistic child set and confirm the predicate flips for at least one populated case.

**One spelling of a construct is not coverage of the construct.** Where a parser routes two accepted spellings of one thing through different callbacks -- a self-closing tag and its bare form -- a counter built on those callbacks can balance for one spelling and not the other, while the test pinning whichever spelling the author typed reads as "this class is handled". Enumerate the spellings the real producer emits.

### Constructing the object-under-test below the layer that transforms it

**Symptom:** The fix lives in an upstream transform (parser, normalizer, `from_api_response`), but the test builds the object via the leaf constructor with the already-correct value -- the transform never runs; green test, broken production.

**Fix:** Feed the test the raw pre-transform input (API payload, unparsed dict), never the leaf constructor, so the transform under test executes.

### Synchronous adapters hide timing-dependent races

**Symptom:** Parallel requests through a zero-latency mock settle in the same microtask, so a dedup/coalescing guard passes -- under real wire latency, staggered arrivals miss the window and spawn N operations.

**Fix:** Inject controllable latency (fake timers, staggered deferred resolution); assert the guard holds for arrival-staggered bursts, not just same-tick ones.

**Reproducing the race deterministically.** Spawning N processes, or sleeping between the two steps, hits the window intermittently, and a fixture that fails two runs in six reads as flake and gets retried away. Release N threads from a single barrier so every participant enters the window on the first round, against a freshly-cold resource each round. Where the race spans an external boundary, use a deterministic hook between the two operations rather than a timing sleep. Validate with a mutant: with the guard removed the fixture must fail every run, not most of them.

### Asserting only presence, never absence

**Symptom:** Payload/serializer tests assert expected fields exist but never that unexpected fields are absent -- a field leaking into a reused builder (CREATE vs UPDATE) passes every existing test.

**Fix:** Where a field set is a contract, pin absence as well as presence: `assert "proof_document_id" not in payload`.

### Looping cases inside one test method

**Symptom:** a table of cases iterated inside a single method. Every reset the framework provides -- transaction rollback, container rebinding, fake state -- is scoped to the method, so cases 2..N run against case 1's leftovers. A uniformly passing run is the shape that hides it.

**Fix:** one case per method, with the control in its own method. Where a loop is unavoidable, assert first on a field that must differ between iterations, and print one identifier the loop did not set -- a repeat of that value is the tell.

### Negative assertions left behind by a relocated observable

**Symptom:** a refactor moves the layer an observable lives at. The positive assertions go red and get fixed; the negatives (`assertNotSent`, "no row written") now hold unconditionally and pass forever, including on the day the guard breaks.

**Fix:** after any such move, sweep the inverted direction: enumerate the subjects the new layer handles, grep every negative assertion naming them, and re-prove each against a planted violation. Confirm the relocated layer is the only path to the observable before calling a hit vacuous.

### A precondition supplied by the fixture, with no production actor

**Symptom:** `setUp()` establishes something nothing in production does -- a seeder that never runs on a deployed environment, a factory default that steers away from the overloaded enum member, a hand-built relation.

**Fix:** for every fixture step, name the production actor that performs the same write, and what request #1 sees if nobody does. An idempotent backfill is not a production write path.

### A bound the regression still satisfies

**Symptom:** `assertLessThanOrEqual(N, queryCount)` with N at or above the unfixed count. It stays green when the fix is reverted, and it also passes at 0.

**Fix:** assert the exact optimized value, or seed two input sizes and assert invariance across them -- the only shape that separates O(1) from O(n). A count invariance proves constant statements, never constant work, so assert a resolved value alongside it.

### A mutation whose application was never asserted

**Symptom:** the mutation never landed (quoting, a wrong anchor, no interpreter inside the container) or landed and tested a different proposition (a body retyped from memory relocates sequenced work; branch structure derived from a filtered view). Either way the run reports PASS, and a broken mutation reads as a credible criticism of someone else's suite.

**Fix:** produce the mutated tree from the ref itself (`git show <ref>:<path>`), assert the token occurs exactly once before writing, and assert both sides after -- new-only token absent, old-only token present -- with fixed-string matching anchored by line content. Keep the assertion on the same side of any container boundary as the edit, and give a zero-valued assertion its own control. Make the restore oracle the artifact (a checksum against `git show`), not a pattern match. Read the file-granularity pass list of a known-bad control: a file green in both runs is a layer that cannot see this class. A passing mutation is a validity signal before it is a coverage finding, and a mutation proves a line is load-bearing, never why.

### Proving a new assertion fires, when the claim was that it was missing

**Symptom:** the coverage gap is argued by mutating the code and watching the new assertion go red. That proves the new assertion has power, not that the pre-fix suite would have missed the defect.

**Fix:** run the same mutation at the pre-fix commit. Only a pass there establishes the gap.

### A fallback test with no guard on the primary path

**Symptom:** the test exercises a retry or fallback only while the primary path still fails. Once upstream is fixed the fallback never runs, and the test keeps passing for a reason it was not written for.

**Fix:** pair it with a guard test asserting the unguarded call still raises the specific error the fallback exists to absorb.

### Two guards with the same observable outcome

**Symptom:** the input trips a header check and a body-parse check alike, so the test proves only that something rejected it -- delete the guard under test and the assertion still holds.

**Fix:** satisfy every guard except the one under test, and assert the specific exception type rather than the shared status code.

### A "string X must not appear in the output" test that contains X

**Symptom:** anything capturing source context -- tracebacks with surrounding lines, error trackers attaching frame locals -- copies the test file into its own output, so the probe reports its own literal and inverts the verdict.

**Fix:** load the needle from a data file, `grep -c` the probe's own source for it and require zero, and assert on structure where possible (the frame's variable map is empty) rather than on a substring.

### A skipped test is green

**Symptom:** a case that skips because its feature, extension, or capability is missing from the build reports as success in every summary the suite prints.

**Fix:** assert that the specific test reported PASS, not that the suite exited zero. Enable whatever the harness helper itself needs -- a helper can pull in unrelated capabilities that each skip for their own reason.

False-pass oracle traps -- the `grep -q` pipefail trap, comparison oracles that fail open, feature-flag-disabled coverage illusions, retiring a suite on count alone, expectations ending in a bare wildcard, conformance harnesses that normalize before comparing, lane gates built on a summary grep, GNU-only matchers in cross-OS assertions, oracles newer than the supported floor, smoke inputs that never reach a budget, and readiness predicates satisfied by a mid-stream match -- are in [false-pass-oracle-traps.md](./false-pass-oracle-traps.md).
