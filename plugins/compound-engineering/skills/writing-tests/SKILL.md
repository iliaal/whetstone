---
name: writing-tests
description: >-
  Generic test writing discipline: test quality, real assertions, anti-patterns,
  and rationalization resistance. Use when writing tests, adding test coverage,
  or fixing failing tests for any language or framework. Complements
  language-specific skills.
---

# Writing Tests

## Core Principle

Tests prove behavior works. A test that can't fail is worthless. A test that tests mocks instead of real code is theater.

## Writing Good Tests

### One behavior per test

Each test should verify exactly one thing. If the test name needs "and" in it, split it into two tests.

```
Good:  "creates user with valid email"
Good:  "rejects user with duplicate email"
Bad:   "creates user and sends welcome email and updates counter"
```

### Derive test cases from user journeys

Before writing test cases for a new feature, enumerate user journeys: "As a [role], I want to [action], so that [benefit]." Generate test cases from each journey -- this ensures tests cover user-visible behavior, not implementation details.

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

**Exception: framework-provided test doubles.** When a framework offers dedicated faking mechanisms (Laravel `Queue::fake()`, `Event::fake()`; React test providers and `vi.mock` for API layers), use them -- they are the idiomatic approach and maintained alongside the framework. The principle is: avoid hand-rolled mocks that drift, not framework-blessed test utilities.

### Tests expose bugs, not the reverse

If a test uncovers broken or buggy behavior, fix the source code -- never adjust the test to match incorrect behavior. A test that passes against a bug is worse than no test at all.

### Assert on outcomes, not implementation

```
Good:  assert user exists in database after create
Bad:   assert repository.save() was called once
Good:  assert response body contains expected fields
Bad:   assert serializer.serialize() was called with user
```

### Test edge cases

For every feature, consider:

- Empty input / null / undefined
- Boundary values (0, 1, max, max+1)
- Invalid types (string where number expected)
- Concurrent access (if applicable)
- Error paths (network failure, timeout, permission denied)
- Unicode and special characters in string inputs

## Red-Green-Refactor (When It Applies)

For bug fixes, writing the failing test first is genuinely valuable -- it proves the bug exists and proves the fix works. For new features, the order is less critical than the quality.

### Bug fixes: test first

1. Write a test that reproduces the bug
2. **Run it and confirm it fails for the right reason** -- a test that fails due to a typo or import error hasn't captured the bug
3. Fix the bug
4. **Run it and confirm it passes AND other tests still pass** -- a fix that breaks something else isn't a fix
5. If the test passes immediately without a fix, you're testing existing behavior, not the bug

This is non-negotiable for bugs -- a fix without a regression test is a fix that will break again.

### New features: test alongside

Write tests as you build, not after. "I'll add tests later" means "I won't add tests."

The goal: by the time the feature is done, tests exist and pass. Whether you wrote the test 5 minutes before or 5 minutes after the code matters less than whether the test exists and is good.

## Anti-Patterns

### Testing mock behavior instead of real behavior

**Symptom:** Test passes but production breaks. Tests assert that mocks were called correctly, not that the actual system works.

**Fix:** Replace mocks with real objects for internal code. Only mock at system boundaries (external APIs, email, payment).

### Test-only methods in production code

**Symptom:** Methods like `reset()`, `clearState()`, `setTestMode()` that exist only because tests need them.

**Fix:** If tests need to reset state, the code has a design problem. Refactor to make state explicit and injectable.

### Snapshot tests as the only test

**Symptom:** All tests are snapshots that get bulk-updated whenever anything changes.

**Fix:** Snapshots catch unintended changes but don't verify correctness. Add behavioral assertions alongside snapshots.

### Testing the framework

**Symptom:** Tests verify that the ORM saves records, the router routes requests, or the framework does what its docs say.

**Fix:** Trust the framework. Test YOUR logic -- the business rules, transformations, and decisions your code makes.

### Incomplete mocks

**Symptom:** Mock only includes the fields the test author knows about. Downstream code consumes other fields and gets undefined.

**Fix:** Mock the COMPLETE data structure as it exists in reality, not just the fields the immediate test uses. Before creating a mock response, check what fields the real API/type contains -- include ALL fields the system might consume downstream. Use real objects or factory-generated fixtures with all fields populated. If you must mock, generate from the real type/schema.

### Mocking without understanding

Before mocking any method, ask: (1) What side effects does the real method have? (2) Does this test depend on any of those side effects? (3) Mock at the lowest level that removes the slow/external part -- not higher.

## When Stuck

| Stuck on... | Do this |
|-------------|---------|
| Don't know how to test | Write the assertion first (desired outcome), then build the test around it |
| Test too complicated | Simplify the interface being tested |
| Must mock everything | Code is too coupled -- use dependency injection |
| Test setup too large | Extract helpers. Still complex? Simplify the design |

## Rationalization Table

When you catch yourself thinking these things, stop:

| Rationalization | Reality |
|----------------|---------|
| "This is too simple to need tests" | Simple code still breaks. Tests document expected behavior. |
| "I manually tested it" | Manual testing is ephemeral -- it can't be re-run, it proves nothing to the next person |
| "Tests will slow me down" | Debugging without tests slows you down more. Tests catch bugs at write time instead of production. |
| "I'll add tests later" | Later never comes. The context you have now is gone later. |
| "The tests would just test the framework" | Then you're not testing your logic. Find the logic and test that. |
| "It's just a refactor, behavior didn't change" | Run the existing tests. If they pass, you're done. If none exist, this is exactly when to add them. |
| "100% coverage is overkill" | Nobody said 100%. But 0% is negligence. Test the important paths. |
| "Mocks are faster" | Mocks are faster to run and slower to maintain. They test assumptions, not behavior. |
| "I already wrote the implementation" | Sunk cost. Tests written after pass immediately and prove nothing about the original bug. |

## Test Quality Checklist

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

This skill is referenced by:
- `workflows:work` -- when adding tests for new functionality (Phase 2)
- `debugging` -- when creating failing tests to reproduce bugs
- `verification-before-completion` -- tests as primary verification evidence

### Tech-Specific Skills

This skill provides generic test discipline. For framework-specific patterns, conventions, and tooling:

- **Laravel/PHP** → `php-laravel` (PHPUnit, factories, feature/unit split, facade faking, data providers)
- **React/TypeScript** → `react-frontend` (Vitest, RTL, component/hook patterns, Playwright E2E, mocking patterns)

Both skills are complementary -- this skill covers principles (why and what to test), tech-specific skills cover implementation (how to test in that framework). When both are active, framework-specific guidance takes precedence for tooling and conventions.
