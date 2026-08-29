---
name: ia-writing-tests
class: discipline
description: >-
  Generic test writing discipline: test quality, real assertions, anti-patterns,
  and rationalization resistance. Use when writing tests, adding test coverage,
  or fixing failing tests for any language or framework. Complements
  language-specific skills.
---

# Writing Tests

## Core Principle

Tests prove behavior works. A test that can't fail is worthless. A test that tests mocks instead of real code is theater.

## Discover the Test Setup First

Before writing the first test, establish what this repository actually runs. Reaching for a default command is how a suite goes green locally and red in CI.

- **Runner and its config**: whichever manifest and test-config file the project's ecosystem uses. Framework-specific detail belongs to the language skills listed under Integration.
- **The checked-in wrapper over any global binary.** A globally installed binary routinely resolves to a different version than the project pins, so prefer the project-local invocation (`uv run pytest` over bare `pytest`, `vendor/bin/phpunit` over `phpunit`).
- **Focused vs. full invocation**: the edit loop needs to run one file or one test; completion needs the whole suite. Learn both forms.
- **Where tests live and how neighbouring test files are named** -- match the existing convention rather than importing one.
- **The command CI gates on** (`.github/workflows/*.yml`). When CI and the README disagree, CI is authoritative.

## Writing Good Tests

### One behavior per test

Each test should verify exactly one thing. If the test name needs "and" in it, split it into two tests.

```
Good:  "creates user with valid email"
Good:  "rejects user with duplicate email"
Bad:   "creates user and sends welcome email and updates counter"
```

### Derive test cases from three sources

Build test coverage from three independent sources and verify every item maps to at least one test:

1. **User requirements** -- what was requested (spec, issue, conversation)
2. **Features implemented** -- what the code actually does (scan the diff)
3. **Claims in the response** -- what is about to be reported to the user as working

Anything in any source with no corresponding test is a coverage gap -- implemented-but-untested features, claimed-but-unverified behavior.

For each acceptance criterion, include at least one discriminating case that a naive wrong implementation would fail. Prefer the negative, boundary, or state-transition case that separates the intended contract from a hard-coded happy path. Do not add a meaningless negative-case quota when one strong case already distinguishes the behavior.

**Make the fixture adversarial on the axis under test.** Realistic sample data carries globally unique ids, distinct values, and non-overlapping keys -- which is exactly what lets a wrong implementation pass. If the contract is a composite key, build a fixture where every child id collides across parents; if it is ordering, give every item the same timestamp. The right fixture is the one a naive implementation cannot survive, not the one that looks most like production.

**An assertion of absence is discriminating only once it has been made to fail.** A test asserting that nothing was written to the shared path, nothing leaked into the production channel, or the fallback was never taken passes identically whether or not the guard works. Plant the forbidden violation and watch that specific assertion fail before trusting it (mechanics under Red-Green-Refactor).

For each source, enumerate user journeys ("As a [role], I want to [action], so that [benefit]") and generate test cases from each, so tests cover user-visible behavior rather than implementation details.

### DAMP over DRY in tests

Each test should be independently readable without chasing shared setup through helpers. Duplication in tests is acceptable -- even desirable -- when it makes intent obvious at a glance. Extract shared setup only when it reduces noise without hiding what the test does.

### Test pyramid

For API/web projects, aim for ~80% unit / ~15% integration / ~5% E2E; adjust for risk profile (data pipelines may need heavier integration, CLI tools minimal E2E).

- **Unit**: fast, isolated, one behavior per test, no database/network/filesystem -- the cheap, fast-feedback foundation.
- **Integration**: verify component boundaries against real dependencies (real test database, wired services, queue producer + consumer) -- catch the wiring bugs mocks hide.
- **E2E**: critical user paths through the real system only (signup, checkout, core workflow) -- every E2E test must justify its maintenance cost.

### Name tests by expected behavior

The test name should describe what happens, not what's being called.

```
Good:  "returns 404 when user does not exist"
Bad:   "test getUserById"
Good:  "sends notification after order is placed"
Bad:   "test processOrder"
```

### Use real objects when practical

Mocks should be a last resort, not a first choice. Every mock is an assumption about behavior that may drift from reality.

| Use real objects for | Use mocks/fakes for |
|---------------------|---------------------|
| Database queries (use test DB) | External HTTP APIs |
| Internal services and classes | Payment gateways |
| File system operations (use temp dirs) | Email/SMS delivery |
| Business logic and transformations | Third-party SDKs with rate limits |

**Exception: framework-provided test doubles.** Framework faking mechanisms (Laravel `Queue::fake()`/`Event::fake()`, React test providers, `vi.mock` for API layers) are idiomatic and maintained alongside the framework -- use them. The rule targets hand-rolled mocks that drift, not framework-blessed utilities.

**Where to cut the mock seam.** When a mock is warranted (the right column above -- external APIs, gateways, delivery services, rate-limited SDKs), place it at the last point owned code touches the unowned resource: mock the payment-client wrapper, not `fetch`; the mailer adapter, not the SMTP transport. Mocking below the wrapper re-implements the third party's behavior inside the test suite and leaves the wrapper's own logic untested. Database queries stay on the left column -- a real test DB, not a mocked repository.

### Tests expose bugs, not the reverse

If a test uncovers broken or buggy behavior, fix the source code -- never adjust the test to match incorrect behavior. A test that passes against a bug is worse than no test at all.

### Test edge cases

For every feature, consider:

- Empty input / null / undefined
- Boundary values (0, 1, max, max+1)
- Invalid types (string where number expected)
- Concurrent access (if applicable)
- Error paths (network failure, timeout, permission denied)
- Unicode and special characters in string inputs

### Silent failure coverage

Tests must detect silent failures, not just happy paths. For every code path that catches, logs, or short-circuits on error, add an assertion that proves the failure was observable. Hunt targets during test writing:

- **Empty catch blocks** (`try { ... } catch {}`) — trigger the error; assert the logger (or equivalent signal) received the original exception.
- **Swallowed rejections** (`.catch(() => [])`, `.catch(() => null)`) — trigger the rejection; assert the caller sees a distinguishable signal (specific return value, logged error, re-thrown).
- **Converted errors** (`catch (e) { return defaultValue; }`) — assert the return value AND that the error was recorded where an operator can find it.
- **Missing async handling** — assert a rejected promise inside the function surfaces as a failure, not just an unhandled-rejection warning.
- **No rollback around transactional work** — assert a mid-transaction failure leaves no partial state (row counts match, queue unchanged).
- **Correlated fallbacks feeding an aggregate** — make every item's dependency fail at once and assert the summary reports *unavailable*, not a clean 0% or 100%. A type-valid placeholder (a neutral verdict, a default score) left in the denominator turns a total outage into a confident, precise, entirely wrong number, and it degrades toward a value that reads as real signal. Assert the unavailable state reaches every surface a human reads, including the one-line summary.

Assertion pattern: instead of `expect(result).toBe(null)` (which passes for both "handled gracefully" and "silent drop"), prefer `expect(logger.error).toHaveBeenCalledWith(expect.any(DatabaseError))` — make the observable signal part of the contract.

## Red-Green-Refactor (When It Applies)

Tests-first answer "what should this do?"; tests-after answer "what does this do?" -- tests written after implementation are biased toward verifying what was built, not what's required. For bug fixes, the failing test first proves the bug exists and the fix works; for new features, the order matters less than the quality.

### Bug fixes: prove-it pattern

1. Write a test that reproduces the bug
2. **Run it and watch it fail** -- confirm it fails for the right reason. A test that fails due to a typo or import error hasn't captured the bug. The failure message should describe the buggy behavior.
3. Apply the fix
4. **Run it and watch it pass** -- confirm the fix addresses the specific failure AND other tests still pass. A fix that breaks something else isn't a fix.
5. If the test passes immediately without a fix, the test is verifying existing behavior, not the bug. Go back to step 1.

**Absence and isolation assertions need a manufactured red phase.** A test that asserts something did *not* happen has no bug in hand to fail against, so it goes green on day one and stays green every day after, including the days the guard is broken. Supply the missing red step: plant exactly the violation the assertion forbids, using a value only this run could produce (a run-unique token, a uniquely-named artifact), and confirm *that specific* assertion fails -- not merely that some assertion fails. Then remove the plant and watch it pass. A fixture that cannot observe the behavior under test passes vacuously in both directions, and nothing else in the suite will notice.

### New features: test alongside

Write tests alongside the implementation, not after. By the time the feature is done, tests exist and pass -- whether a test was written 5 minutes before or 5 minutes after the code matters less than whether it exists and is good.

**Minimum viability during green phase:** When making a test pass, write the simplest code that satisfies it -- not the abstraction that seems "right," not the feature that might be needed next. Refactor only after the test is green.

## Anti-Patterns

Extended rationale, fix ladders, and mechanics for the longer items: [anti-patterns-extended.md](./references/anti-patterns-extended.md).

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

**Fix:** Wait on the observable condition with a deadline -- poll for the record, the event, or the state change (framework helpers: `waitFor`, `assertEventually`, polling with timeout). The deadline bounds the wait; the condition ends it. A sleep placed to *reproduce* a race is the same mistake pointed the other way -- see "Synchronous adapters hide timing-dependent races" for the barrier form.

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

### An aggregate assertion that names no offender

**Symptom:** `assert all(r.returncode == 0 for r in results)` renders as a bare `assert False`. The failure names neither the failing item nor its message, so diagnosing it costs an extra cycle re-running under a patched assertion.

**Fix:** collect the offenders and assert on the list -- `assert [r for r in results if r.returncode != 0] == []` -- so the output carries identity and error text. Same rule for regression pins: pin the specific offending names, not a count. A defect of this class re-enters as a different plausible-looking value, and a count notices nothing.

### Persistent test infrastructure state contamination

**Symptom:** Integration tests fail with row-count multipliers (expected 2 rows, got 8) yet pass on a fresh container -- persistent infrastructure kept state from prior runs. **Diagnostic shortcut:** a clean integer multiple (2x, 3x, 4x...) between expected and actual means state contamination, not a logic bug -- logic bugs rarely produce uniform multipliers across unrelated assertions.

**Fix:** Reset infrastructure state between runs -- ephemeral containers, fixture `TRUNCATE`, or volume teardown (ladder in the reference); never rely on tests "cleaning up after themselves."

Isolation and sandbox traps -- containerized-timeout leaks, a harness sandboxing the subject in the primitive under test, global before/after snapshots, and relocated environment variables -- are in [isolation-and-sandbox-traps.md](./references/isolation-and-sandbox-traps.md).

### Vacuous forall over an empty collection

**Symptom:** A `forall`-style assertion (`every`, `all`, `.iter().all()`) passes vacuously -- the factory never attached children, and every such operator returns `true` over an empty collection.

**Fix:** Attach a realistic child set and confirm the predicate flips for at least one populated case.

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

False-pass oracle traps -- the `grep -q` pipefail trap, comparison oracles that fail open, feature-flag-disabled coverage illusions, and retiring a suite on count alone -- are in [false-pass-oracle-traps.md](./references/false-pass-oracle-traps.md).

## When Stuck

| Stuck on... | Do this |
|-------------|---------|
| Don't know how to test | Write the assertion first (desired outcome), then build the test around it |
| Test too complicated | Simplify the interface being tested |
| Must mock everything | Code is too coupled -- use dependency injection |
| Test setup too large | Extract helpers that reduce noise without hiding test intent (see DAMP). Still complex? Simplify the design |

## Rationalization Table

If about to skip, defer, or argue against writing a test for any reason, STOP and load [rationalization-table.md](./references/rationalization-table.md) first. Thirteen common excuses with their counter-truths. When arguing against writing a test, the argument is probably lost.

## Verify

Before considering tests complete:

- [ ] Every new public function/endpoint has at least one test
- [ ] Each test has a descriptive name stating expected behavior
- [ ] Tests use real objects where possible (mocks only at system boundaries)
- [ ] Edge cases covered (empty, null, boundary, error paths)
- [ ] Each acceptance criterion has a discriminating case a naive wrong implementation would fail
- [ ] Every absence or isolation assertion was proven able to fail -- the forbidden violation was planted with a run-unique value and that specific assertion failed
- [ ] Tests assert on outcomes, not implementation details
- [ ] Snapshot, golden, fixture, and generated-expectation changes were reviewed semantically rather than regenerated to obtain green
- [ ] Tests are independent -- no shared mutable state between tests. If tests pass individually but fail together, use bisection to find the polluter (run one-by-one in isolation until the offending test is found)
- [ ] Tests run fast enough to run frequently (< 30 seconds for unit suite)
- [ ] Bug fix tests reproduce the original bug

## Integration

This skill covers generic test discipline. For framework-specific patterns, conventions, and tooling:

- **Laravel/PHP** → `ia-php-laravel` (PHPUnit, factories, feature/unit split, facade faking, data providers)
- **React/TypeScript** → `ia-react-frontend` (Vitest, RTL, component/hook patterns, Playwright E2E, mocking patterns)

When both are active, framework-specific guidance takes precedence for tooling and conventions.
