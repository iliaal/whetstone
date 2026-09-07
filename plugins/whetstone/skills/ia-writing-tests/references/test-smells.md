# test smells

## Anti-Patterns

Extended rationale, fix ladders, and mechanics for the longer items: [anti-patterns-extended.md](./anti-patterns-extended.md).

### Reaching for a default test command

**Symptom:** the bare global runner passes locally, while CI invokes the project-pinned wrapper and fails on a different dependency set or a different runner entirely.

**Fix:** Establish the runner, the checked-in wrapper, and the CI command before writing tests (see "Discover the Test Setup First").

### Host-local wrappers inside tracked test scripts

**Symptom:** a checked-in test script invokes a tool that exists only on the author's machine -- an agent shell wrapper, a personal alias, a locally-installed helper. On a bare CI runner, in a container, or on a colleague's machine every otherwise-correct assertion fails before reaching the code under test.

**Fix:** a tracked test is a portable artifact. Use ordinary POSIX tools inside it and apply any local wrapper to the *outer* invocation instead. Declare genuinely required non-standard dependencies in CI configuration, and grep the test tree for local wrappers before enabling a hosted gate.

### Testing mock behavior instead of real behavior

**Symptom:** Test passes but production breaks. Tests assert that mocks were called correctly, not that the actual system works.

**Fix:** Replace mocks with real objects for internal code (see "Use real objects when practical").

### Sleeping instead of waiting on a condition

**Symptom:** `sleep(2)` / `setTimeout` / `time.sleep()` before asserting on async work. A sleep is a race condition with a timer attached: too short flakes under load, long enough is wasted wall-clock in every run forever.

**Fix:** Wait on the observable condition with a deadline -- poll for the record, the event, or the state change (framework helpers: `waitFor`, `assertEventually`, polling with timeout). The deadline bounds the wait; the condition ends it. A sleep placed to *reproduce* a race is the same mistake pointed the other way -- see "Synchronous adapters hide timing-dependent races" for the barrier form. Write the readiness predicate so it cannot match mid-stream: an alternation that ORs the real marker with a cheap one (a blank line, a token the producer can print more than once) is satisfied on the first poll, and the half-written artifact then reads as a wrong answer rather than an incomplete one.

### Asserting elapsed wall-clock time

**Symptom:** the test calls the real timer and asserts `now() - started >= 100`. That tests the runtime clock and scheduler, not the code's delay policy -- millisecond rounding reports 99 on a run that plainly took longer, and a re-run goes green without any code change.

**Fix:** inject the sleep boundary and assert the policy: the exact delay requested, the cap applied (6000 becomes 5000), and the ordering (the wait resolves before the dependent call). Keep a real-timer test only where integration with the runtime timer is itself the contract, and then use a monotonic clock with a documented tolerance, never a one-millisecond lower bound.

### Re-running a flaky test to green

**Symptom:** A test fails intermittently and the response is re-run until it passes. Each re-run silences a detector -- the flake is a real race, ordering dependency, or shared-state bug in the test or the code.

**Fix:** Treat flaky as red: fix it now, or skip it visibly with a reason and an owner (a linked issue, a named TODO) so it cannot quietly rot. Never leave it in the suite passing-by-retry.

### Test-only methods in production code

**Symptom:** Methods like `reset()`, `clearState()`, `setTestMode()` that exist only because tests need them.

**Fix:** If tests need to reset state, the code has a design problem. Refactor to make state explicit and injectable.

### Snapshot tests as the only test

**Symptom:** All tests are snapshots that get bulk-updated whenever anything changes.

**Fix:** Snapshots catch unintended changes but don't verify correctness. Add behavioral assertions alongside snapshots.

### Change detector

**Symptom:** the test fails only when an intentional decision changes -- a constant's value, exact wording, private structure -- so it fires on every redesign and sleeps through real bugs.

**Fix:** assert the consumer-visible outcome the decision drives, not the decision's literal value -- same fix as Implementation-echo assertions: assert the consumer-visible outcome.

### Regenerating expected output to obtain green

**Symptom:** A snapshot, golden, fixture, or generated expectation is replaced wholesale after a failure, with no review of what behavior changed.

**Fix:** Treat expected-output changes as specification changes. Inspect the semantic diff, explain why the new output is intended, and verify the behavior with an independent assertion or exercised entry point. Follow any repository-specific approval marker for golden changes. If the implementation is wrong, fix the implementation instead of regenerating the oracle.

### Testing the framework

**Symptom:** Tests verify that the ORM saves records, the router routes requests, or the framework does what its docs say.

**Fix:** Trust the framework. Test the project's own logic -- the business rules, transformations, and decisions the code makes.

### Incomplete mocks

**Symptom:** Mock only includes the fields the test author knows about. Downstream code consumes other fields and gets undefined.

**Fix:** Mock the COMPLETE data structure as it exists in reality -- check what fields the real API/type contains and include everything consumed downstream. Prefer real objects or factory fixtures with all fields populated; if mocking is unavoidable, generate from the real type/schema.

### Mocking without understanding

Before mocking any method, ask: (1) What side effects does the real method have? (2) Does this test depend on any of those side effects? (3) Mock at the lowest level that removes the slow/external part -- not higher.

### AI-generated test smells

LLM-written tests (including self-written) fail in predictable ways. **Before committing, scan every test for these six smells:**

- **Mock of the system under test** — mocking the very function being tested, so the test asserts what the mock returned. Always a mistake. Delete the mock; call the real function.
- **Circular assertion** — computing the expected value the same way the code computes the actual value (`expect(sum(a,b)).toBe(a+b)`). The test passes even when both are wrong. Replace with a hand-computed expected value or a known fixture.
- **Snapshot of unreviewed output** — first-run snapshot committed without reading it. The snapshot enshrines whatever the code happened to emit, bugs included. Hand-write the first snapshot or diff it line by line before accepting.
- **Assertion-free exercise** — test calls the function, checks nothing, passes because nothing threw. Every test needs at least one `expect(...)` / `assert ...` tied to the behavior under test.
- **Over-broad matchers** — `expect(result).toBeTruthy()` on a function that returns an object. Passes for `{}`, `true`, `"anything"`, all equally. Pin to the specific shape.
- **Implementation-echo assertions** — `expect(repo.save).toHaveBeenCalledTimes(1)` when the real contract is "the user exists in the database afterward." Assert on outcomes (row exists, response body contains expected fields), not call counts or internal method invocations.
