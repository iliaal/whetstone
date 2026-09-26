# Behavioral review

Use this checklist on independently selected tests, including files with no detector
hits. Follow fixture and assertion-helper definitions before judging a test body.

## Trace the source of the answer

Identify the exact behavior under review. Compare the operation that should compute
the answer with the operation the test actually invokes.

| Suspect shape | Evidence needed | Useful counterexample or repair |
|---|---|---|
| Mock supplies the subject's answer | The replaced operation itself owns the claimed transformation, persistence, or decision. No real owner runs. | Change that owner to return an incorrect value. Call the real owner with a fake only at its dependency boundary. |
| Fixture constructs the finished result | The test hand-builds the saved record, rendered payload, receipt, or callback order that production should produce. | Stop production from producing that result. Feed the test raw input through the real producer. |
| Self-derived expected value | Expected and actual share the same implementation or the expected object is compared to itself. | Break the shared computation. Use an independently specified answer or property that constrains the result. |
| Type/truthiness/presence only | The name promises particular values, selection, order, or effects, but any object/non-null/array succeeds. | Return a wrong value of the same type, an empty collection, or omit the claimed effect. Assert meaningful contents. |
| Test reimplements the algorithm | Only the test's copy executes or the oracle repeats the same decision with the same failure modes. | Change the production algorithm and trace whether any assertion depends on it. |

An independent oracle may compute its answer. A simple mathematical relation or a
different reference algorithm is not automatically circular. Shared bugs require a
concrete explanation, not merely a visual resemblance between calculations.

## Make competing behaviors produce different answers

| Claim | Fixture that hides the regression | Discriminating input |
|---|---|---|
| Sort or select minimum | Input is already in the expected order. | Entries arrive out of order with distinct keys. |
| Compute median | One/two values, or symmetric values where mean equals median. | Skewed values such as 0, 100, 900. |
| Apply several filters | Every rejected row also fails another filter. | One excluded row per filter that satisfies all other filters. |
| Preserve manual selection | Automatic selection would choose the same item. | Observer input favors a different item while the override is active. |
| Reject just one invalid property | Fixture violates multiple earlier checks. | Valid control plus exactly one invalid dimension; inspect the intended refusal. |
| Keep no writes/queries/events | Empty inputs, disabled path, fixed-empty fake, or unchanged coarse timestamp. | Reach the live path; observe the effect independently; prove a planted effect is visible. |
| All results satisfy a property | Result collection can be empty. | Assert expected population or identities before the universal property. |
| Coalesce repeated requests | Only one request or requests that never overlap. | Same-key overlapping requests with controlled scheduling; observe one shared operation. |
| Keep independent requests separate | Only one key, so incorrect merging remains invisible. | Distinct keys with independently asserted outcomes. |
| Process concurrently | One item or synchronous completion hides serialization. | Multiple items and controlled scheduling that distinguishes concurrent entry from sequential work. |
| Handle unknown ID | No existing records, so ignoring the requested ID still returns empty. | Seed a competing record and assert that its values do not appear. |

Do not invent unsupported input shapes. Trace producer constraints when reachability
is uncertain. A test of one valid equivalence class need not cover every other class;
report the missing distinction only within the behavior the test claims.

## Follow failure into the runner

- In pytest/unittest, returning `False` does not fail the test. Printed errors and
  caught exceptions can also finish successfully. Check failure branches for an
  assertion, rethrow, or runner failure call.
- Check whether a prerequisite branch returns normally, skips visibly, or fails.
  A skip is honest nonexecution but still leaves the behavior unverified.
- Check that async work and rejection assertions are awaited or returned to the
  runner. Confirm assertions in callbacks actually execute before test completion.
- Inspect `if`, loops, catch blocks, and helper return values around assertions.
  An assertion that is never reached provides no protection.
- Acceptance of success and failure together, such as status in `(200, 500)`, cannot
  establish successful service behavior. Identify the exact contract before judging
  an allowed set of outcomes.
- For negatives, inspect the actual error and the path producing it. A bare exception
  or status can be sufficient when that is the contract and the fixture reaches the
  relevant operation. Do not require fragile message text universally.
- Read matcher semantics. An `any`/`assertSent` predicate returning true for unrelated
  items lets those items satisfy the check. A `not called` assertion on a detached
  spy never observes the live operation.

## Keep legitimate doubles and narrow tests

Retain these when the real subject makes the asserted decision:

- External transport mocked while real code builds and sends an exact payload.
- A callback spy asserting arguments, call count, or ordering when delegation is the
  documented contract. It does not also prove downstream persistence.
- A fake child component exposing props or lifecycle events while a real parent
  decides forwarding, mounting, or remounting.
- A throwing collaborator that drives a real transaction rollback or fallback.
- A fake clock, scheduler, or barrier that makes real retry/concurrency logic observable.
- A no-throw test for a documented input that actually invokes the real operation and
  propagates exceptions. A dummy assertion adds no value but does not erase that check.
- Source, snapshot, or configuration assertions that independently pin required bytes,
  schema, packaging, or release contracts. Exactness alone is not evidence of junk.

Do not classify tests by mock volume, class-name matching, incident IDs, assertion
counts, or whether they use a database. An incident reference explains intent; the
assertion still needs to distinguish the regression.

## Sources and calibration

Google's [test-double guidance](https://testing.googleblog.com/2013/07/testing-on-toilet-know-your-test-doubles.html)
distinguishes stubs, interaction mocks, and functional fakes. Their roles depend on the
boundary being tested.

[Testing Library's principles](https://testing-library.com/docs/guiding-principles/)
favor tests exercised through the interfaces users interact with. Apply that principle
within the stated test layer rather than demanding every test be end-to-end.

[Stryker's mutation states](https://stryker-mutator.io/docs/mutation-testing-elements/mutant-states-and-metrics/)
distinguish survivors, uncovered code, and invalid mutants. A mutation result measures
response to selected changes; it is not a percentage of bad tests. Check equivalent
mutants and assertion relevance before turning survivors into quality findings.
