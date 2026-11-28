# Detector diagnostics and blind spots

Read before trusting any detector output. The detectors are discovery aids; their
results never bound the semantic audit.

## Exit status and completeness

All four static detectors (weak-negative, duplicate, guard, and junit census) return
status 2 when an input glob matches no file. The weak-negative and duplicate CLIs also
return 2 for other known incomplete input and can still print useful partial findings.
The census also returns 2 on an unreadable report. For the reach probe, inspect pytest's
terminal summary for an incomplete-evidence diagnostic before using its report.
Run each detector's `--help` for its contract instead of reading the source.
Duplicate JSON includes `input_complete`, `unmatched_patterns`, `unsupported_files`,
`unparsed_files`, and `unrecognized_files`.

These describe known file-level omissions; `input_complete: true` does not prove every
test or syntax form was recognized. A zero-test file may be a helper or unsupported
syntax. Reconcile omissions with the inventory before proceeding.

## Known blind spots (require source review)

- An unrelated assertion, a printed exception, or a comment can make the weak-negative
  detector consider an error pinned. Status membership and some unittest assertions
  are not detected. JS/PHP/Rust parsing is heuristic; supported extensions do not imply
  complete framework syntax support.
- The guard scanner counts textual occurrences, including unused strings. Its unpinned
  total is not a coverage estimate or an estimate of defective tests.
- JUnit names may lack file paths. The census prefers explicit paths and qualified
  module names. Short names and stems can identify one file only when unique in the
  supplied inventory. Resolve the separately listed ambiguous files and suspected
  collection gaps with runner output.
- Duplicate detection does not resolve every fixture, provider, hook, or module mock.
  Same executed lines or body shape do not establish equivalent contracts. Statically
  inactive JS/TS tests appear separately and cannot substitute for active tests in a
  comparison group. Check the actual gate for conditional skips and focused tests.

## Consolidation leads

Treat REDUNDANT/SUBSUMED/FOLD/PARAMETRIZE detector groups as separate consolidation
leads, not findings. Inspect setup and contract differences before merging. Preserve
distinct risks across unit, integration, and end-to-end layers. Report deletions and
LOC only when deletion or consolidation is part of the requested work. Apply the
test-deletion bar in [mutation-and-repair.md](./mutation-and-repair.md) before
recommending removal.
