# Per-stack commands

Run instrumentation and mutations only in an isolated scratch copy for read-only
audits. Preserve the user's current source and relevant local changes in that copy.
The commands below support the semantic review in `SKILL.md`; they do not replace it.

Tool names and flags below were current when written. Confirm each with `--help` or the
tool's docs before running it, and prefer the repository's pinned wrapper over a global
binary. Install audit-only tools ad hoc, for example with `uvx`, `npx`, or a scratch
Composer project. Never add them as project dependencies without approval.

Each section covers three things:
- **junit**: how to get the junit report to read for skips and collection gaps. Produce it with the gate's
  own command plus the reporter flag, so the census reflects gate conditions.
- **reach**: how to see which guard actually refused.
- **mutation**: a tool for confirming one candidate. Scope it to the candidate's
  file; whole-suite runs are too slow to be routine.

For the Python, PHP, and JavaScript reporter commands below, create a fresh
report directory for each gate invocation with
`audit_report_dir=$(mktemp -d)`. Keep the gate and census in the same shell and
pass `"$audit_report_dir/gate.xml"` to the reporter, then read that file.
Record the gate's exit status separately. Read only the report produced by that
invocation; a missing report means incomplete audit input, never a fallback to
an earlier report. Use separate directories for concurrent packages and retries.

## Python

- **junit:** `pytest --junitxml="$audit_report_dir/gate.xml"`, appended to the gate's pytest command.
- **reach, CLI-driven suites:** in the scratch copy, temporarily print the failing
  subprocess's stderr and exit status next to the assertion, run the test, and read
  which guard refused. Restore the test afterwards.
- **reach, in-process code:** temporarily replace `pytest.raises(X)` with
  `pytest.raises(X) as e` and print `e.value`. For a web client, print
  `response.json()` next to the status assertion.
- **mutation:** `mutmut`, scoped to one module.

## Rust

- **junit:** `cargo nextest` writes junit when the selected profile sets
  `[profile.<name>.junit] path = "junit.xml"` in the nextest config; with
  `--profile ci` the report lands in `target/nextest/ci/junit.xml`. Plain
  `cargo test` has no junit output. Use `cargo test -- --list` against
  `cargo test -- --list --ignored` to find `#[ignore]` tests. Also check whether the
  gate enables the features that `#[cfg(feature = "...")]` test modules need.
- **reach:** replace `assert!(r.is_err())` with a `println!` of `r.unwrap_err()` and run
  with `-- --nocapture`. For binaries driven by a Python or shell harness, use that
  harness's reach probe.
- **mutation:** `cargo mutants`, restricted to the file under suspicion. Its test command
  can be the repository's process-test runner.

## PHP (PHPUnit, Pest, Laravel)

- **junit:** `vendor/bin/phpunit --log-junit "$audit_report_dir/gate.xml"`; Pest accepts the same
  flag. PHPUnit's junit carries an `assertions` count per test, so the report also
  shows executed tests with zero assertions.
- **uncollected files:** tests outside the `<testsuite>` directories in `phpunit.xml`,
  or classes whose file name lacks the configured suffix (default `Test.php`), never
  run. Pass `--test-files 'tests/**/*.php'` to the census.
- **reach:** in a copy of the candidate test, add `$this->withoutExceptionHandling()`
  before the request, so the real exception class and message surface instead of a
  rendered 403, 404, 409, or 422. A 403 can come from a policy, a gate, middleware,
  or a form request's `authorize()`. A 422 can come from any rule. Assert the
  validation key (`assertJsonValidationErrors(['field'])`) or the message.
- **mutation:** Infection, filtered to the candidate's source file.

## JavaScript and TypeScript (Vitest, Jest, Playwright)

- **junit:** `vitest run --reporter=junit --outputFile="$audit_report_dir/gate.xml"`. Jest needs the
  `jest-junit` reporter. Playwright's `--reporter=junit` prints to stdout
  unless `PLAYWRIGHT_JUNIT_OUTPUT_FILE="$audit_report_dir/gate.xml"` (or the reporter's `outputFile`
  config option) names a file. In a pnpm or other
  workspace, run the census per package, or pass several reports.
- **uncollected files:** Vitest and Jest `include`/`testMatch` globs, and workspace
  packages whose `test` script is missing or ends in `|| true`, silently drop tests.
- **application bootstrap:** A fixture-installed guard, pipe, interceptor, or serializer
  can pass while the deployed app omits it. For claims about the app's installed
  behavior, exercise its production bootstrap or the same shared registration path.
  Keep fixture registration for focused tests of the component itself.
- **type assertions:** Vitest's `expectTypeOf` and `assertType` are [compile-time checks](https://vitest.dev/guide/testing-types.html).
  A green runtime-only run does not prove them. Verify that a blocking gate enables
  Vitest typechecking or runs a compiler that includes the assertion files. Inspect
  the applicable tsconfig and, for Vitest typechecking, `typecheck.include`.
  In the isolated audit copy, change one expected type to an incompatible type.
  Require that same gate to fail on the type mismatch.
- **reach:** change a bare `.toThrow()` to `.toThrow(/expected message/)`, or
  `console.log` the rejected error. For request tests, log the response body beside
  the status assertion.
- **skips:** `it.skip`, `describe.skip`, `test.todo`, and `it.skipIf(...)`/`it.runIf(...)`
  whose condition is constant in CI all appear as skipped in junit.
- **mutation:** StrykerJS, with its mutate glob set to the candidate file.

## Where guard messages live per stack

| Stack | Source globs to search | Literals to skip |
|---|---|---|
| Rust | `'src/**/*.rs'` (in-file `#[cfg(test)]` code is counted as tests) | `'^[a-z_]+$'` for identifier-like literals |
| Python | `'src/**/*.py'`, `'app/**/*.py'` | log-format strings |
| PHP/Laravel | `'app/**/*.php'` | `'^[\w.]+$'` for translation keys and config paths |
| JS/TS | `'src/**/*.ts'`, `'apps/*/src/**/*.ts'` | i18n keys |

In Laravel, validation messages mostly come from language files rather than
`app/**`. For those rules, a key assertion such as `assertJsonValidationErrors` is the
pin, not the message text.

