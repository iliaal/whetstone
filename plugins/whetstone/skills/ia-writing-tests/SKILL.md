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

Assertion pattern: instead of `expect(result).toBe(null)` (which passes for both "handled gracefully" and "silent drop"), prefer `expect(logger.error).toHaveBeenCalledWith(expect.any(DatabaseError))` — make the observable signal part of the contract.

## Red-Green-Refactor (When It Applies)

Tests-first answer "what should this do?"; tests-after answer "what does this do?" -- tests written after implementation are biased toward verifying what was built, not what's required. For bug fixes, the failing test first proves the bug exists and the fix works; for new features, the order matters less than the quality.

### Bug fixes: prove-it pattern

1. Write a test that reproduces the bug
2. **Run it and watch it fail** -- confirm it fails for the right reason. A test that fails due to a typo or import error hasn't captured the bug. The failure message should describe the buggy behavior.
3. Apply the fix
4. **Run it and watch it pass** -- confirm the fix addresses the specific failure AND other tests still pass. A fix that breaks something else isn't a fix.
5. If the test passes immediately without a fix, the test is verifying existing behavior, not the bug. Go back to step 1.

### New features: test alongside

Write tests alongside the implementation, not after. By the time the feature is done, tests exist and pass -- whether a test was written 5 minutes before or 5 minutes after the code matters less than whether it exists and is good.

**Minimum viability during green phase:** When making a test pass, write the simplest code that satisfies it -- not the abstraction that seems "right," not the feature that might be needed next. Refactor only after the test is green.

## Anti-Patterns

Extended rationale, fix ladders, and mechanics for the longer items: [anti-patterns-extended.md](./references/anti-patterns-extended.md).

### Reaching for a default test command

**Symptom:** the bare global runner passes locally, while CI invokes the project-pinned wrapper and fails on a different dependency set or a different runner entirely.

**Fix:** Establish the runner, the checked-in wrapper, and the CI command before writing tests (see "Discover the Test Setup First").

### Testing mock behavior instead of real behavior

**Symptom:** Test passes but production breaks. Tests assert that mocks were called correctly, not that the actual system works.

**Fix:** Replace mocks with real objects for internal code (see "Use real objects when practical").

### Test-only methods in production code

**Symptom:** Methods like `reset()`, `clearState()`, `setTestMode()` that exist only because tests need them.

**Fix:** If tests need to reset state, the code has a design problem. Refactor to make state explicit and injectable.

### Snapshot tests as the only test

**Symptom:** All tests are snapshots that get bulk-updated whenever anything changes.

**Fix:** Snapshots catch unintended changes but don't verify correctness. Add behavioral assertions alongside snapshots.

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

### Persistent test infrastructure state contamination

**Symptom:** Integration tests fail with row-count multipliers (expected 2 rows, got 8) yet pass on a fresh container -- persistent infrastructure kept state from prior runs. **Diagnostic shortcut:** a clean integer multiple (2x, 3x, 4x...) between expected and actual means state contamination, not a logic bug -- logic bugs rarely produce uniform multipliers across unrelated assertions.

**Fix:** Reset infrastructure state between runs -- ephemeral containers, fixture `TRUNCATE`, or volume teardown (ladder in the reference); never rely on tests "cleaning up after themselves."

### Vacuous forall over an empty collection

**Symptom:** A `forall`-style assertion (`every`, `all`, `.iter().all()`) passes vacuously -- the factory never attached children, and every such operator returns `true` over an empty collection.

**Fix:** Attach a realistic child set and confirm the predicate flips for at least one populated case.

### Constructing the object-under-test below the layer that transforms it

**Symptom:** The fix lives in an upstream transform (parser, normalizer, `from_api_response`), but the test builds the object via the leaf constructor with the already-correct value -- the transform never runs; green test, broken production.

**Fix:** Feed the test the raw pre-transform input (API payload, unparsed dict), never the leaf constructor, so the transform under test executes.

### Synchronous adapters hide timing-dependent races

**Symptom:** Parallel requests through a zero-latency mock settle in the same microtask, so a dedup/coalescing guard passes -- under real wire latency, staggered arrivals miss the window and spawn N operations.

**Fix:** Inject controllable latency (fake timers, staggered deferred resolution); assert the guard holds for arrival-staggered bursts, not just same-tick ones.

### Asserting only presence, never absence

**Symptom:** Payload/serializer tests assert expected fields exist but never that unexpected fields are absent -- a field leaking into a reused builder (CREATE vs UPDATE) passes every existing test.

**Fix:** Where a field set is a contract, pin absence as well as presence: `assert "proof_document_id" not in payload`.

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
- [ ] Tests assert on outcomes, not implementation details
- [ ] Tests are independent -- no shared mutable state between tests. If tests pass individually but fail together, use bisection to find the polluter (run one-by-one in isolation until the offending test is found)
- [ ] Tests run fast enough to run frequently (< 30 seconds for unit suite)
- [ ] Bug fix tests reproduce the original bug

## Integration

This skill covers generic test discipline. For framework-specific patterns, conventions, and tooling:

- **Laravel/PHP** → `ia-php-laravel` (PHPUnit, factories, feature/unit split, facade faking, data providers)
- **React/TypeScript** → `ia-react-frontend` (Vitest, RTL, component/hook patterns, Playwright E2E, mocking patterns)

When both are active, framework-specific guidance takes precedence for tooling and conventions.
