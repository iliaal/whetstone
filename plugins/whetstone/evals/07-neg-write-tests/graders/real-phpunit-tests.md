---
type: llm
focus: last_message
---
Pass only if ALL hold:
1. The response contains a PHPUnit test class (extends `TestCase`, methods prefixed `test` or attributed `#[Test]`).
2. At least one test asserts `isValid` returns true for a valid slug AND at least one asserts false for an invalid slug (too short, too long, uppercase, leading/trailing/double hyphen, or disallowed character).
3. Every assertion checks a real outcome of `isValid`; tautologies such as `assertTrue(true)` or asserting on a hard-coded value that never calls the validator fail. A characterization test that pins current (even buggy) behavior is a real assertion and is fine.
4. The tests are the deliverable. Commentary about defects the tests expose (for example the `$` anchor accepting a trailing newline) is acceptable and does not fail this grader. Fail only if the response replaces the test class with a code-review report, or presents a severity-ranked findings list with a merge verdict instead of tests.
