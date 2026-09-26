# ia-test-audit Specification

## Intent

`ia-test-audit` is a `workflow`-class skill (a multi-step process producing concrete artifacts). Audit whether tests detect regressions in the behavior they claim to protect. Find mocked-away subjects, weak or circular assertions, undiscriminating fixtures, swallowed failures, and tests missing from gates. Use for test-quality audits, suspected false confidence in generated tests, and reviewing new tests. Use ia-writing-tests for writing tests.

## Scope

In scope:
- Behaviors described in `SKILL.md` and routed via the should_trigger phrasings in `distillery/tests/fixtures/triggers/ia-test-audit.jsonl`.
- Updates to runtime behavior, structure, trigger precision, references, and validation.

Out of scope:
- Acting as the runtime instructions themselves (those live in `SKILL.md`).
- Trigger phrasings already covered by adjacent `ia-*` skills (`validate-plugin` flags >70% description overlap as DUPLICATE_TRIGGER).
- <!-- to fill in: domain-specific exclusions when the skill drifts -->

## Trigger Context

- Class: `workflow`
- Hook regex: `plugins/whetstone/hooks/skill-patterns.sh` -> `SKILL_PATTERNS[ia-test-audit]`
- Common requests (from fixture should_trigger):
  - "audit the tests in the billing module for false confidence"
  - "do these tests actually catch a regression in the discount logic?"
  - "assess the test suite for mocked-away subjects"
- Should not trigger for (from fixture should_not_trigger):
  - "write tests for the user service"
  - "add test coverage for the auth module"
  - "the test quality is poor, improve it"

## Source And Evidence Model

Authoritative sources:

- `SKILL.md` -- runtime instructions and reference routing.
- `references/*.md` -- bundled supplementary content (4 file(s)).
- `scripts/*.py` -- five bundled stdlib-only detectors and probes (`weak_negatives.py`, `duplicate_tests.py`, `guard_pins.py`, `junit_census.py`, `pytest_reach_probe.py`); require Python 3.11+.
- `distillery/scripts/test_ia_test_audit_detectors.py` -- pytest CLI tests for the bundled scripts.
- `distillery/tests/fixtures/triggers/ia-test-audit.jsonl` -- positive and negative trigger phrasings under regression test.
- `plugins/whetstone/hooks/skill-patterns.sh` -- regex pattern that fires this skill.
- `distillery/.eval-data/ia-test-audit/` -- harvested session examples (when present).

Data that must not be stored in this skill or its references:

- Secrets, credentials, tokens.
- Machine-specific filesystem paths (`/home/...`, `/Users/...`, `~/ai/...`). The validator (`MACHINE_PATH_LEAK`) flags these as HIGH.
- Private URLs, customer data, or unredacted personal information.

### Coverage matrix

| Dimension | Status | Evidence |
|---|---|---|
| Trigger fixtures | complete | distillery/tests/fixtures/triggers/ia-test-audit.jsonl (>=5 should_trigger, >=5 should_not_trigger) |
| Hook regex pattern | complete | plugins/whetstone/hooks/skill-patterns.sh (`SKILL_PATTERNS[ia-test-audit]`) |
| Reference architecture | complete | 4 file(s) under references/ |
| Bundled scripts | partial | 5 scripts under scripts/; CLI tests in distillery/scripts/test_ia_test_audit_detectors.py; next: add CLI tests for guard_pins.py, junit_census.py, and pytest_reach_probe.py |
| Real-usage signal | <!-- populated by harvest-sessions when sessions exist --> | distillery/.eval-data/ia-test-audit/ (created by harvest-sessions) |

## Evaluation

Lightweight (run on every change):

```bash
python3 distillery/scripts/distiller.py validate-plugin --component ia-test-audit
python3 distillery/scripts/distiller.py test-triggers --skill ia-test-audit
python3 -m pytest -q distillery/scripts/test_ia_test_audit_detectors.py
```

Deeper (when behavior risk warrants):

```bash
python3 distillery/scripts/distiller.py dspy-eval ia-test-audit
python3 distillery/scripts/distiller.py diagnose-negatives ia-test-audit
```

Acceptance gates:
- `validate-plugin --component ia-test-audit` returns 0 HIGH findings.
- `test-triggers --skill ia-test-audit` returns F1 = 1.0 with floors of 5 should_trigger and 5 should_not_trigger.
- For dspy-eval, the composite score does not regress against the most recent saved baseline (see `distillery/.eval-data/ia-test-audit/history.json`).

## Known Limitations

- The scripts require Python 3.11+ (`duplicate_tests.py` uses `ast.TryStar`); under 3.10 it fails with a traceback, not a version message.
- `pytest_reach_probe.py` patches only `subprocess.Popen.communicate`; `subprocess.call`, `check_call`, bare `Popen.wait()`, `os.system`, and asyncio subprocesses are not observed. It runs the target suite, so it belongs in a scratch copy.
- The detectors are lead generators with documented blind spots (`references/detectors.md`); no hits never bounds the semantic audit.

## Maintenance Notes

- Update `SKILL.md` when the runtime workflow, branch conditions, or output contract changes.
- Update this `SPEC.md` when intent, scope, evidence model, evaluation gates, or maintenance expectations change.
- Update the trigger fixture when adding new positive phrasings, removing stale ones, or expanding scope (the 5/5 floor is a hard validator gate).
- Update the hook regex in `skill-patterns.sh` whenever fixture positives expose a missed phrasing; verify F1 = 1.0 with `eval-triggers` before committing.
- Run the full release pipeline via `/release` -- never bump versions or update CHANGELOG.md from a per-skill edit.
