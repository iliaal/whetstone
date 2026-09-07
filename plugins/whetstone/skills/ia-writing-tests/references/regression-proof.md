# regression proof

## Red-Green-Refactor (When It Applies)

Tests-first answer "what should this do?"; tests-after answer "what does this do?" -- tests written after implementation are biased toward verifying what was built, not what's required. For bug fixes, the failing test first proves the bug exists and the fix works; for new features, the order matters less than the quality.

### Bug fixes: prove-it pattern

1. Write a test that reproduces the bug
2. **Run it and watch it fail** -- confirm it fails for the right reason. A test that fails due to a typo or import error hasn't captured the bug. The failure message should describe the buggy behavior.
3. Apply the fix
4. **Run it and watch it pass** -- confirm the fix addresses the specific failure AND other tests still pass. A fix that breaks something else isn't a fix.
5. If the test passes immediately without a fix, the test is verifying existing behavior, not the bug. Go back to step 1.

**Absence and isolation assertions need a manufactured red phase.** A test that asserts something did *not* happen has no bug in hand to fail against, so it goes green on day one and stays green every day after, including the days the guard is broken. Supply the missing red step: plant exactly the violation the assertion forbids, using a value only this run could produce (a run-unique token, a uniquely-named artifact), and confirm *that specific* assertion fails -- not merely that some assertion fails. Then remove the plant and watch it pass. A fixture that cannot observe the behavior under test passes vacuously in both directions, and nothing else in the suite will notice.

**The manufactured red phase needs its own two guards.** A negative control that stubs enforcement, rebuilds, and watches the fixture fail is evidence only if the stub applied *and* the artifact was built from it: a scripted replace that matches nothing returns the input unchanged with no error, and a build queued behind another on the same lock can publish an artifact from pre-stub source. Assert the edit changed the file, print an applied-marker the control can read back, and run the control only once that specific build invocation's own exit status is in hand -- a timestamp proves staleness in one direction and nothing in the other. The tell is an implausible pass, not an error.

### New features: test alongside

Write tests alongside the implementation, not after. By the time the feature is done, tests exist and pass -- whether a test was written 5 minutes before or 5 minutes after the code matters less than whether it exists and is good.

**Minimum viability during green phase:** When making a test pass, write the simplest code that satisfies it -- not the abstraction that seems "right," not the feature that might be needed next. Refactor only after the test is green.
