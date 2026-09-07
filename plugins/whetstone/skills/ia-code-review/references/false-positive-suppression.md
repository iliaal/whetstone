# False Positive Suppression

Not every potential issue is worth raising. False positives waste author attention and erode trust in the review process.

## Suppression Categories

Before reporting a finding, check whether it falls into one of these categories. If it does, suppress it.

### 1. Pre-existing issues

The finding exists in code that was NOT changed in this diff. Don't raise issues on surrounding code unless they interact directly with the changes. If surrounding code has a real problem that's exposed by the change, note it as informational with the distinction clear.

### 2. Linter/formatter covered

Style issues that the project's linter or formatter already enforces. Don't duplicate automated tooling. If tooling is missing, distinguish a documented convention violation from a personal preference.

### 3. Intentional design

Code that looks unusual but is deliberately written that way. Signals: comment explaining why, consistent pattern elsewhere in codebase, matches a documented architectural decision, performance-critical section. When uncertain, use question-based feedback ("Was this intentional?") rather than flagging it as a defect. Exception: an explanatory comment does not suppress a gate-loosening finding (skipped test, new suppression comment, lowered threshold -- the floor-guards class) -- a comment is how silent loosening is normally dressed, so those report with the comment quoted as context.

### 4. Already handled elsewhere

The "issue" is actually handled in a different layer (middleware validates input, framework handles escaping, type system prevents the error class). Verify the handling exists before suppressing.

### 5. Generic suggestions

"Consider using X instead of Y" without evidence that Y causes a problem in this specific context. Suggestions need a concrete reason: performance data, maintainability argument tied to this codebase, security concern with evidence.

### 6. Framework/library internals

Flagging patterns that are idiomatic for the framework in use. Examples: Laravel facades, React hook dependency arrays with stable references, Go error wrapping patterns. Review the code against its framework's conventions, not abstract ideals.

### 7. Test-specific patterns

Test code follows different rules than production code. Don't flag: hardcoded test data, assertion-heavy functions, mock setup boilerplate, test helper utilities that duplicate production logic for clarity. Do flag: tests that don't actually assert anything, tests that test the mock instead of real behavior.

### 8. Readability-aiding redundancy

"X is redundant with Y" when the redundancy aids readability. "Add a comment explaining this threshold" when thresholds change during tuning and comments rot. "This assertion could be tighter" when it already covers the behavior. Consistency-only reformatting to match adjacent code style. "Regex doesn't handle edge case X" when input is constrained and X never occurs. Anything the author already fixed in a later commit within the same diff, flagged in their own PR comments, or resolved by a prior reviewer.

## When to Override Suppression

A category is not a substitute for checking the actual case. An intentional design or framework idiom can still introduce a concrete defect; report that consequence with the stated rationale as context. Conversely, a severe-sounding bug class does not override a verified guard, lack of reachability, or the selected review scope. Use the evidence and impact rubric in [severity-and-confidence.md](./severity-and-confidence.md); preserve consequential uncertainty in Residual Risks.
