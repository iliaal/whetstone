# ia-linux-bash-scripting Specification

## Intent

`ia-linux-bash-scripting` is a `language`-class skill (stack-specific patterns and idioms). Defensive Bash scripting for Linux: safe foundations, argument parsing, production patterns, ShellCheck compliance. Use when writing bash scripts, shell scripts, cron jobs, or CLI tools in bash.

## Scope

In scope:
- Behaviors described in `SKILL.md` and routed via the should_trigger phrasings in `distillery/tests/fixtures/triggers/ia-linux-bash-scripting.jsonl`.
- Updates to runtime behavior, structure, trigger precision, references, and validation.

Out of scope:
- Acting as the runtime instructions themselves (those live in `SKILL.md`).
- Trigger phrasings already covered by adjacent `ia-*` skills (`validate-plugin` flags >70% description overlap as DUPLICATE_TRIGGER).
- <!-- to fill in: domain-specific exclusions when the skill drifts -->

## Trigger Context

- Class: `language`
- Hook regex: `plugins/whetstone/hooks/skill-patterns.sh` -> `SKILL_PATTERNS[ia-linux-bash-scripting]`
- Common requests (from fixture should_trigger):
  - "write a bash script to automate the database backup"
  - "create a deployment script for the production servers"
  - "write a bash script to rotate the nightly backups"
- Should not trigger for (from fixture should_not_trigger):
  - "build a React form with validation"
  - "add a new Laravel middleware for API throttling"
  - "write a Python CLI for log parsing"

## Source And Evidence Model

Authoritative sources:

- `SKILL.md` -- runtime instructions and reference routing.
- `references/*.md` -- bundled supplementary content (0 file(s)).
- `distillery/tests/fixtures/triggers/ia-linux-bash-scripting.jsonl` -- positive and negative trigger phrasings under regression test.
- `plugins/whetstone/hooks/skill-patterns.sh` -- regex pattern that fires this skill.
- `distillery/.eval-data/ia-linux-bash-scripting/` -- harvested session examples (when present).

Data that must not be stored in this skill or its references:

- Secrets, credentials, tokens.
- Machine-specific filesystem paths (`/home/...`, `/Users/...`, `~/ai/...`). The validator (`MACHINE_PATH_LEAK`) flags these as HIGH.
- Private URLs, customer data, or unredacted personal information.

### Coverage matrix

| Dimension | Status | Evidence |
|---|---|---|
| Trigger fixtures | complete | distillery/tests/fixtures/triggers/ia-linux-bash-scripting.jsonl (>=5 should_trigger, >=5 should_not_trigger) |
| Hook regex pattern | complete | plugins/whetstone/hooks/skill-patterns.sh (`SKILL_PATTERNS[ia-linux-bash-scripting]`) |
| Reference architecture | n/a | no references; SKILL.md is self-contained |
| Real-usage signal | <!-- populated by harvest-sessions when sessions exist --> | distillery/.eval-data/ia-linux-bash-scripting/ (created by harvest-sessions) |

## Evaluation

Lightweight (run on every change):

```bash
python3 distillery/scripts/distiller.py validate-plugin --component ia-linux-bash-scripting
python3 distillery/scripts/distiller.py test-triggers --skill ia-linux-bash-scripting
```

Deeper (when behavior risk warrants):

```bash
python3 distillery/scripts/distiller.py dspy-eval ia-linux-bash-scripting
python3 distillery/scripts/distiller.py diagnose-negatives ia-linux-bash-scripting
```

Acceptance gates:
- `validate-plugin --component ia-linux-bash-scripting` returns 0 HIGH findings.
- `test-triggers --skill ia-linux-bash-scripting` returns F1 = 1.0 with floors of 5 should_trigger and 5 should_not_trigger.
- For dspy-eval, the composite score does not regress against the most recent saved baseline (see `distillery/.eval-data/ia-linux-bash-scripting/history.json`).

## Known Limitations

<!-- to fill in over time as drift surfaces. Default rule: any time diagnose-negatives
     surfaces a recurring failure pattern, document it here so future maintainers
     understand the trade-off the current implementation accepts. -->

## Maintenance Notes

- Update `SKILL.md` when the runtime workflow, branch conditions, or output contract changes.
- Update this `SPEC.md` when intent, scope, evidence model, evaluation gates, or maintenance expectations change.
- Update the trigger fixture when adding new positive phrasings, removing stale ones, or expanding scope (the 5/5 floor is a hard validator gate).
- Update the hook regex in `skill-patterns.sh` whenever fixture positives expose a missed phrasing; verify F1 = 1.0 with `eval-triggers` before committing.
- Run the full release pipeline via `/release` -- never bump versions or update CHANGELOG.md from a per-skill edit.
