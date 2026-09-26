# Mutation probes and repairs

Read before running a focused mutation to confirm a finding, before changing any test
or production code, and before proposing deletion of a production seam. The
evidence-status labels and scratch-copy rule in `SKILL.md` step 4 still apply.

## Focused mutation procedure

Work in an isolated scratch copy that preserves the current working-tree contents,
including relevant uncommitted changes.

1. Run the unchanged selected test and record executed/skipped counts.
2. Apply one plausible behavior regression to production code in the copy. Before
   writing, assert that the edited token occurs exactly once in the target file.
3. Inspect the exact diff and verify that the tested import or binary uses that copy.
4. Run the same test. Confirm its actual assertion result, not only process exit status.
5. Establish that the mutation changes an in-scope contract on reachable inputs.
6. Restore the source and verify the baseline again when reusing the copy.

## Reading the result

A surviving mutant proves a gap only for that mutation and selected tests. A compile
error, collection error, unrelated failure, timeout, or skipped test is not evidence
that the intended assertion detects the regression. Equivalent mutations are not gaps.

If feasible, add a scratch-only discriminating assertion and show that baseline passes
and mutant fails for the intended reason. Label that proof separately from the unchanged
test's survival. Do not present scratch controls as shipped tests.

Use targeted mutation as discovery as well as confirmation when useful. Do not require
an expensive whole-suite mutation campaign. Search neighboring coverage before making
a suite-wide claim; identify stronger existing tests when they already catch the defect.

## Repairs and authoring

When changes are authorized, repair the claimed protection first. Keep valid boundary
mocks, no-throw smoke contracts, static contract checks, and distinct test layers.
Do not replace every mock with infrastructure or assert private details unnecessarily.

For each repair, choose an input and assertion that distinguish the correct behavior
from the named regression. Validate unchanged-test survival where feasible, then prove
the repaired test passes on baseline and fails on that regression. Run focused tests
and repository-required gates for the affected files. Never weaken an assertion or
regenerate expected output merely to obtain green.

History, absence of production callers, and replacement coverage are required when
proposing deletion of a production seam. They are not prerequisites for reporting a
weak assertion. Public APIs, plugins, reflection, and dynamic registration can be live
without an obvious local caller. No-callers search alone does not prove dead code.

Handle detector consolidation groups per [detectors.md](./detectors.md).

When authoring a new test, answer the same six trace questions in `SKILL.md` step 2. A
regression test must fail on the defective behavior for the intended reason. A test
need not prove the entire system to provide independent, useful protection at its
stated boundary.
