# test completion

## When Stuck

| Stuck on... | Do this |
|-------------|---------|
| Don't know how to test | Write the assertion first (desired outcome), then build the test around it |
| Test too complicated | Simplify the interface being tested |
| Must mock everything | Code is too coupled; use dependency injection |
| Test setup too large | Extract helpers that reduce noise without hiding test intent (see DAMP). Still complex? Simplify the design |

## Rationalization Table

Before skipping or deferring a test, load [rationalization-table.md](./rationalization-table.md). Distinguish a missing test seam from the excuses listed there.

## No reachable seam for the actual trigger

Use the missing-seam exception from ia-debugging only when a test cannot exercise the bug as it actually triggered, such as a production-data defect, a hardware dependency, or a race without a reproducible interleaving. For a race, first attempt a test-only controlled interleaving. Retain the test only if it reproduces the actual trigger. Keep cheap, reachable regression tests. Expense, deadline, or difficulty alone does not establish a missing seam. A test that cannot reach the trigger is not regression proof.

Record the missing seam and the discriminating verification actually run. State the behavior each check exercised and its observed result. Distinguish narrower evidence from no evidence for the original defect. If the original trigger remains unverified, report that limit and do not claim the bug repaired. Preserve user acceptance criteria and repository-required gates; the exception does not waive them or authorize interface changes solely to manufacture a test seam.

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
- [ ] Tests are independent: no shared mutable state between tests. If tests pass individually but fail together, recover the failing order and bisect the predecessors together with the victim in one process (see the test-pollution section of ia-debugging root-cause tracing). Running files one at a time in isolation never reproduces an in-process leak such as a module singleton, unrestored mock, or global timer; use a per-file artifact scan only when the pollution leaves a file behind
- [ ] Tests run fast enough to run frequently (< 30 seconds for unit suite)
- [ ] Bug fix tests reproduce the original trigger, or the missing seam and actual verification limits are reported under the exception above
- [ ] Mutation check run: mentally mutate the code (wrong constant, flipped branch, dropped side effect, empty/default return) and confirm some test fails for each

## Integration

This skill covers generic test discipline. For framework-specific patterns, conventions, and tooling:

- **Laravel/PHP** → `ia-php-laravel` (PHPUnit, factories, feature/unit split, facade faking, data providers)
- **React/TypeScript** → `ia-react-frontend` (Vitest, RTL, component/hook patterns, Playwright E2E, mocking patterns)

When both are active, framework-specific guidance takes precedence for tooling and conventions.
