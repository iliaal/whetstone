# test design

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

### When trivial code earns a test

Getters, constructors, constants, and pass-through wrappers earn a test only if they validate, normalize, default, derive, enforce, or carry a side effect -- otherwise assert the first consumer-visible result that depends on them.

### Derive test cases from three sources

Build test coverage from three independent sources and verify every item maps to at least one test:

1. **User requirements** -- what was requested (spec, issue, conversation)
2. **Features implemented** -- what the code actually does (scan the diff)
3. **Claims in the response** -- what is about to be reported to the user as working

Anything in any source with no corresponding test is a coverage gap -- implemented-but-untested features, claimed-but-unverified behavior.

For each acceptance criterion, include at least one discriminating case that a naive wrong implementation would fail. Prefer the negative, boundary, or state-transition case that separates the intended contract from a hard-coded happy path. Do not add a meaningless negative-case quota when one strong case already distinguishes the behavior.

**Make the fixture adversarial on the axis under test.** Realistic sample data carries globally unique ids, distinct values, and non-overlapping keys -- which is exactly what lets a wrong implementation pass. If the contract is a composite key, build a fixture where every child id collides across parents; if it is ordering, give every item the same timestamp. The right fixture is the one a naive implementation cannot survive, not the one that looks most like production. The default fixture also tends to select the container's fast internal representation -- sequential keys, short strings, and small maps take a packed or inline layout, so the restructure or rehash path never executes. When a change touches a container's internals, build one case whose keys, size, or contents force the alternate representation, and confirm it fails without the fix.

**An assertion of absence is discriminating only once it has been made to fail.** A test asserting that nothing was written to the shared path, nothing leaked into the production channel, or the fallback was never taken passes identically whether or not the guard works. Plant the forbidden violation and watch that specific assertion fail before trusting it (mechanics under Red-Green-Refactor).

For each source, enumerate user journeys ("As a [role], I want to [action], so that [benefit]") and generate test cases from each, so tests cover user-visible behavior rather than implementation details.

### Differential-fuzz anything that must byte-match another implementation

Hand-written cases pick round values and miss the format's conditional branches. Generate a few thousand values per type shape from the reference implementation itself, compare the two outputs, and include nested and composite shapes -- a fast path for leaf values inherits every scalar bug it delegates to. Commit a representative slice as fixed cases, and re-run the full sweep on every change to either side.

Two longer generation techniques -- building a corpus as the cross-product of a table's axes instead of hand-picking cases, and proving a mechanical refactor behavior-preserving with a reflection-driven transcript -- are in [generated-corpus-techniques.md](./generated-corpus-techniques.md).

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
