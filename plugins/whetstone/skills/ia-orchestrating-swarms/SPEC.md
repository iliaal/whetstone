# ia-orchestrating-swarms Specification

## Intent

`ia-orchestrating-swarms` is a `workflow`-class skill (a multi-step process producing concrete artifacts). Coordinate multi-agent swarms for parallel and pipeline workflows. Use when coordinating multiple agents, running parallel reviews, building pipeline workflows, or implementing divide-and-conquer patterns with subagents.

## Scope

In scope:
- Behaviors described in `SKILL.md` and routed via the should_trigger phrasings in `distillery/tests/fixtures/triggers/ia-orchestrating-swarms.jsonl`.
- Updates to runtime behavior, structure, trigger precision, references, and validation.

Out of scope:
- Acting as the runtime instructions themselves (those live in `SKILL.md`).
- Trigger phrasings already covered by adjacent `ia-*` skills (`validate-plugin` flags >70% description overlap as DUPLICATE_TRIGGER).
- <!-- to fill in: domain-specific exclusions when the skill drifts -->

## Trigger Context

- Class: `workflow`
- Hook regex: `plugins/whetstone/hooks/skill-patterns.sh` -> `SKILL_PATTERNS[ia-orchestrating-swarms]`
- Common requests (from fixture should_trigger):
  - "run a multi-agent review of the entire codebase"
  - "use parallel agents to analyze each module independently"
  - "prevent agents from echoing each other in the multi-agent review"
- Should not trigger for (from fixture should_not_trigger):
  - "write a cron job for nightly backups"
  - "add validation to the registration form"
  - "write a unit test for one helper function"

## Source And Evidence Model

Authoritative sources:

- `SKILL.md` -- runtime instructions and reference routing.
- `references/*.md` -- bundled supplementary content (15 file(s)).
- `distillery/tests/fixtures/triggers/ia-orchestrating-swarms.jsonl` -- positive and negative trigger phrasings under regression test.
- `plugins/whetstone/hooks/skill-patterns.sh` -- regex pattern that fires this skill.
- `distillery/.eval-data/ia-orchestrating-swarms/` -- harvested session examples (when present).

Data that must not be stored in this skill or its references:

- Secrets, credentials, tokens.
- Machine-specific filesystem paths (`/home/...`, `/Users/...`, `~/ai/...`). The validator (`MACHINE_PATH_LEAK`) flags these as HIGH.
- Private URLs, customer data, or unredacted personal information.

### Coverage matrix

| Dimension | Status | Evidence |
|---|---|---|
| Trigger fixtures | complete | distillery/tests/fixtures/triggers/ia-orchestrating-swarms.jsonl (>=5 should_trigger, >=5 should_not_trigger) |
| Hook regex pattern | complete | plugins/whetstone/hooks/skill-patterns.sh (`SKILL_PATTERNS[ia-orchestrating-swarms]`) |
| Reference architecture | complete | 15 file(s) under references/ |
| Real-usage signal | <!-- populated by harvest-sessions when sessions exist --> | distillery/.eval-data/ia-orchestrating-swarms/ (created by harvest-sessions) |

## Evaluation

Lightweight (run on every change):

```bash
python3 distillery/scripts/distiller.py validate-plugin --component ia-orchestrating-swarms
python3 distillery/scripts/distiller.py test-triggers --skill ia-orchestrating-swarms
```

Deeper (when behavior risk warrants):

```bash
python3 distillery/scripts/distiller.py dspy-eval ia-orchestrating-swarms
python3 distillery/scripts/distiller.py diagnose-negatives ia-orchestrating-swarms
```

Acceptance gates:
- `validate-plugin --component ia-orchestrating-swarms` returns 0 HIGH findings.
- `test-triggers --skill ia-orchestrating-swarms` returns F1 = 1.0 with floors of 5 should_trigger and 5 should_not_trigger.
- For dspy-eval, the composite score does not regress against the most recent saved baseline (see `distillery/.eval-data/ia-orchestrating-swarms/history.json`).

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
