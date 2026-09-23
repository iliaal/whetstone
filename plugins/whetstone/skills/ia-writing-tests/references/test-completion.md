# test completion

## When Stuck

| Stuck on... | Do this |
|-------------|---------|
| Don't know how to test | Write the assertion first (desired outcome), then build the test around it |
| Test too complicated | Simplify the interface being tested |
| Must mock everything | Code is too coupled; use dependency injection |
| Test setup too large | Extract helpers that reduce noise without hiding test intent (see DAMP). Still complex? Simplify the design |

## Rationalization Table

If about to skip, defer, or argue against writing a test for any reason, STOP and load [rationalization-table.md](./rationalization-table.md) first. Thirteen common excuses with their counter-truths. When arguing against writing a test, the argument is probably lost.

## Verify

Before considering tests complete:

- [ ] Every new public function/endpoint has at least one test
- [ ] Each test has a descriptive name stating expected behavior
- [ ] Tests use real objects where possible (mocks only at system boundaries)
- [ ] Edge cases covered (empty, null, boundary, error paths)
- [ ] Each acceptance criterion has a discriminating case a naive wrong implementation would fail
- [ ] Every absence or isolation assertion was proven able to fail: the forbidden violation was planted with a run-unique value and that specific assertion failed
- [ ] Tests assert on outcomes, not implementation details
- [ ] Snapshot, golden, fixture, and generated-expectation changes were reviewed semantically rather than regenerated to obtain green
- [ ] Tests are independent: no shared mutable state between tests. If tests pass individually but fail together, use bisection to find the polluter (run one-by-one in isolation until the offending test is found)
- [ ] Tests run fast enough to run frequently (< 30 seconds for unit suite)
- [ ] Bug fix tests reproduce the original bug
- [ ] Mutation check run: mentally mutate the code (wrong constant, flipped branch, dropped side effect, empty/default return) and confirm some test fails for each

## Integration

This skill covers generic test discipline. For framework-specific patterns, conventions, and tooling:

- **Laravel/PHP** → `ia-php-laravel` (PHPUnit, factories, feature/unit split, facade faking, data providers)
- **React/TypeScript** → `ia-react-frontend` (Vitest, RTL, component/hook patterns, Playwright E2E, mocking patterns)

When both are active, framework-specific guidance takes precedence for tooling and conventions.
