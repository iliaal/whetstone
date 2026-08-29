# ia-planning Specification

## Intent

`ia-planning` is a `workflow`-class skill (a multi-step process producing concrete artifacts). It plans software implementation when unresolved decisions, dependency depth, or session continuity justify an artifact. It keeps phases vertical, process work bound to named capability, and authorized implementation moving without a ceremonial handoff.

## Scope

In scope:
- Behaviors described in `SKILL.md` and routed via the should_trigger phrasings in `distillery/tests/fixtures/triggers/ia-planning.jsonl`.
- Updates to runtime behavior, structure, trigger precision, references, and validation.

Out of scope:
- Acting as the runtime instructions themselves (those live in `SKILL.md`).
- Trigger phrasings already covered by adjacent `ia-*` skills (`validate-plugin` flags >70% description overlap as DUPLICATE_TRIGGER).
- <!-- to fill in: domain-specific exclusions when the skill drifts -->

## Trigger Context

- Class: `workflow`
- Hook regex: `plugins/whetstone/hooks/skill-patterns.sh` -> `SKILL_PATTERNS[ia-planning]`
- Common requests (from fixture should_trigger):
  - "plan the implementation of the search feature"
  - "break down this feature into tasks"
  - "create a plan for the database migration"
- Should not trigger for (from fixture should_not_trigger):
  - "debug why the tests are failing"
  - "review the code in this PR"
  - "add a new endpoint for user profiles"

## Source And Evidence Model

Authoritative sources:

- `SKILL.md` -- runtime instructions and reference routing.
- `references/*.md` -- bundled supplementary content (2 file(s)).
- `distillery/tests/fixtures/triggers/ia-planning.jsonl` -- positive and negative trigger phrasings under regression test.
- `plugins/whetstone/hooks/skill-patterns.sh` -- regex pattern that fires this skill.
- `distillery/.eval-data/ia-planning/` -- harvested session examples (when present).

Data that must not be stored in this skill or its references:

- Secrets, credentials, tokens.
- Machine-specific filesystem paths (`/home/...`, `/Users/...`, `~/ai/...`). The validator (`MACHINE_PATH_LEAK`) flags these as HIGH.
- Private URLs, customer data, or unredacted personal information.

### Coverage matrix

| Dimension | Status | Evidence |
|---|---|---|
| Trigger fixtures | complete | distillery/tests/fixtures/triggers/ia-planning.jsonl (>=5 should_trigger, >=5 should_not_trigger) |
| Hook regex pattern | complete | plugins/whetstone/hooks/skill-patterns.sh (`SKILL_PATTERNS[ia-planning]`) |
| Reference architecture | complete | 2 file(s) under references/ |
| Outcome discipline | complete | `SKILL.md` When to Plan, Plan Quality Rules, Task Rules, and Execution Handoff |
| Real-usage signal | <!-- populated by harvest-sessions when sessions exist --> | distillery/.eval-data/ia-planning/ (created by harvest-sessions) |

## Evaluation

Lightweight (run on every change):

```bash
python3 distillery/scripts/distiller.py validate-plugin --component ia-planning
python3 distillery/scripts/distiller.py test-triggers --skill ia-planning
```

Deeper (when behavior risk warrants):

```bash
python3 distillery/scripts/distiller.py dspy-eval ia-planning
python3 distillery/scripts/distiller.py diagnose-negatives ia-planning
```

Acceptance gates:
- `validate-plugin --component ia-planning` returns 0 HIGH findings.
- `test-triggers --skill ia-planning` returns F1 = 1.0 with floors of 5 should_trigger and 5 should_not_trigger.
- For dspy-eval, the composite score does not regress against the most recent saved baseline (see `distillery/.eval-data/ia-planning/history.json`).

## Known Limitations

- Planning thresholds remain judgment-based because file and tool-call counts do not measure decision or integration risk reliably.
- `.plan/task_plan.md` is ephemeral recovery state, not a shipped project artifact or evidence of implementation progress.

## Maintenance Notes

- Update `SKILL.md` when the runtime workflow, branch conditions, or output contract changes.
- Update this `SPEC.md` when intent, scope, evidence model, evaluation gates, or maintenance expectations change.
- Update the trigger fixture when adding new positive phrasings, removing stale ones, or expanding scope (the 5/5 floor is a hard validator gate).
- Update the hook regex in `skill-patterns.sh` whenever fixture positives expose a missed phrasing; verify F1 = 1.0 with `eval-triggers` before committing.
- Run the full release pipeline via `/release` -- never bump versions or update CHANGELOG.md from a per-skill edit.
