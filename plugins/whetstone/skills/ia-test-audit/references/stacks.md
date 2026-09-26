# Per-stack commands

Run instrumentation and mutations only in an isolated scratch copy for read-only
audits. Preserve the user's current source and relevant local changes in that copy.
The commands below support the semantic review in `SKILL.md`; they do not replace it.

Tool names and flags below were current when written. Confirm each with `--help` or the
tool's docs before running it, and prefer the repository's pinned wrapper over a global
binary. Install audit-only tools ad hoc, for example with `uvx`, `npx`, or a scratch
Composer project. Never add them as project dependencies without approval.

Each section covers three things:
- **junit**: how to get the report `junit_census.py` reads. Produce it with the gate's
  own command plus the reporter flag, so the census reflects gate conditions.
- **reach**: how to see which guard actually refused.
- **mutation**: a tool for confirming one candidate. Scope it to the candidate's
  file; whole-suite runs are too slow to be routine.

## Python

- **junit:** `pytest --junitxml=/tmp/gate.xml`, appended to the gate's pytest command.
- **reach, CLI-driven suites:** in the scratch copy, run
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<this skill's directory>/scripts REACH_PROBE_OUT=/tmp/reach.jsonl
  pytest -p pytest_reach_probe <tests>`, then
  `python3 <this skill's directory>/scripts/pytest_reach_probe.py /tmp/reach.jsonl`.
  The probe runs the suite and patches only `subprocess.Popen.communicate`, so it sees
  `subprocess.run` and wrappers built on `run` or `communicate`. It does not observe
  `subprocess.call`, `check_call`, a bare `Popen(...).wait()`, `os.system`, or asyncio
  subprocesses; silence from the probe is not evidence that no call failed.
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

- **junit:** `vendor/bin/phpunit --log-junit /tmp/gate.xml`; Pest accepts the same
  flag. PHPUnit's junit carries an `assertions` count per test, so `junit_census.py`
  also reports executed tests with zero assertions.
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

- **junit:** `vitest run --reporter=junit --outputFile=/tmp/gate.xml`. Jest needs the
  `jest-junit` reporter. Playwright's `--reporter=junit` prints to stdout
  unless `PLAYWRIGHT_JUNIT_OUTPUT_FILE=/tmp/gate.xml` (or the reporter's `outputFile`
  config option) names a file. In a pnpm or other
  workspace, run the census per package, or pass several reports.
- **uncollected files:** Vitest and Jest `include`/`testMatch` globs, and workspace
  packages whose `test` script is missing or ends in `|| true`, silently drop tests.
- **reach:** change a bare `.toThrow()` to `.toThrow(/expected message/)`, or
  `console.log` the rejected error. For request tests, log the response body beside
  the status assertion.
- **skips:** `it.skip`, `describe.skip`, `test.todo`, and `it.skipIf(...)`/`it.runIf(...)`
  whose condition is constant in CI all appear as skipped in junit.
- **mutation:** StrykerJS, with its mutate glob set to the candidate file.

## Guard-message extraction hints for `guard_pins.py`

| Stack | Useful `--src` | Useful `--exclude` |
|---|---|---|
| Rust | `'src/**/*.rs'` (in-file `#[cfg(test)]` code is counted as tests) | `'^[a-z_]+$'` for identifier-like literals |
| Python | `--src 'src/**/*.py' --src 'app/**/*.py'` | log-format strings |
| PHP/Laravel | `'app/**/*.php'` | `'^[\w.]+$'` for translation keys and config paths |
| JS/TS | `--src 'src/**/*.ts' --src 'apps/*/src/**/*.ts'` | i18n keys |

In Laravel, validation messages mostly come from language files rather than
`app/**`. For those rules, a key assertion such as `assertJsonValidationErrors` is the
pin, not the message text.

## What `duplicate_tests.py` resolves per stack

| Stack | Resolved | Not resolved |
|---|---|---|
| Python | fixture parameters, `parametrize` cases (a plain test can match one case), module constants, same-module helper defaults, observation bindings | conftest fixture bodies, imported helpers and constants, `setUp` state |
| Rust | `let` locals; `#[rstest]`/`#[test_case]` attributes as the data source | helper bodies; each parametrized fn is one unit |
| PHP | `$variables`; `->assert*` chains split from the request; data provider name and parameters as the data source | `setUp`, `$this->` properties (a stateful body pairs only within its own file), provider rows |
| JS/TS | `const`/`let`/`var` locals; `it.each` tables as the data source | `beforeEach`, module-level mocks, reordered statements |

The status, polarity, harness, and clique gates apply to every stack. Two refinements are
Python only: literals that select what to read are not counted as signal, and a test whose
only calls load fixtures counts as observation-only.

Pairs stay within one file by default. `--cross-file` hunts copy-pasted tests, but a
copied body usually tests a different copy of the code, so it is not redundant with the
original.
