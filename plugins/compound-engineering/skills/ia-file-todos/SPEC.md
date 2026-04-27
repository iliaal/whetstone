# ia-file-todos Specification

## Intent

`ia-file-todos` is a `tool`-class skill (a narrow utility scoped to a single capability). File-based todo and task tracking in the todos/ directory. Use when creating, triaging, listing, or managing todo files, tracking work items, managing the backlog, converting PR comments to tracked tasks, or checking todo status and dependencies.

## Scope

In scope:
- Behaviors described in `SKILL.md` and routed via the should_trigger phrasings in `distillery/tests/fixtures/triggers/ia-file-todos.jsonl`.
- Updates to runtime behavior, structure, trigger precision, references, and validation.

Out of scope:
- Acting as the runtime instructions themselves (those live in `SKILL.md`).
- Trigger phrasings already covered by adjacent `ia-*` skills (`validate-plugin` flags >70% description overlap as DUPLICATE_TRIGGER).
- <!-- to fill in: domain-specific exclusions when the skill drifts -->

## Trigger Context

- Class: `tool`
- Hook regex: `plugins/compound-engineering/hooks/skill-patterns.sh` -> `SKILL_PATTERNS[ia-file-todos]`
- Common requests (from fixture should_trigger):
  - "set up the todo directory for tracking work items"
  - "manage the file-based todo list for this sprint"
  - "manage todos for this refactor"
- Should not trigger for (from fixture should_not_trigger):
  - "optimize the image processing pipeline"
  - "add WebSocket support for real-time notifications"
  - "close the GitHub issue for this bug"

## Source And Evidence Model

Authoritative sources:

- `SKILL.md` -- runtime instructions and reference routing.
- `references/*.md` -- bundled supplementary content (2 file(s)).
- `distillery/tests/fixtures/triggers/ia-file-todos.jsonl` -- positive and negative trigger phrasings under regression test.
- `plugins/compound-engineering/hooks/skill-patterns.sh` -- regex pattern that fires this skill.
- `distillery/.eval-data/ia-file-todos/` -- harvested session examples (when present).

Data that must not be stored in this skill or its references:

- Secrets, credentials, tokens.
- Machine-specific filesystem paths (`/home/...`, `/Users/...`, `~/ai/...`). The validator (`MACHINE_PATH_LEAK`) flags these as HIGH.
- Private URLs, customer data, or unredacted personal information.

### Coverage matrix

| Dimension | Status | Evidence |
|---|---|---|
| Trigger fixtures | complete | distillery/tests/fixtures/triggers/ia-file-todos.jsonl (>=5 should_trigger, >=5 should_not_trigger) |
| Hook regex pattern | complete | plugins/compound-engineering/hooks/skill-patterns.sh (`SKILL_PATTERNS[ia-file-todos]`) |
| Reference architecture | complete | 2 file(s) under references/ |
| Real-usage signal | <!-- populated by harvest-sessions when sessions exist --> | distillery/.eval-data/ia-file-todos/ (created by harvest-sessions) |

## Evaluation

Lightweight (run on every change):

```bash
python3 distillery/scripts/distiller.py validate-plugin --component ia-file-todos
python3 distillery/scripts/distiller.py test-triggers --skill ia-file-todos
```

Deeper (when behavior risk warrants):

```bash
python3 distillery/scripts/distiller.py dspy-eval ia-file-todos
python3 distillery/scripts/distiller.py diagnose-negatives ia-file-todos
```

Acceptance gates:
- `validate-plugin --component ia-file-todos` returns 0 HIGH findings.
- `test-triggers --skill ia-file-todos` returns F1 = 1.0 with floors of 5 should_trigger and 5 should_not_trigger.
- For dspy-eval, the composite score does not regress against the most recent saved baseline (see `distillery/.eval-data/ia-file-todos/history.json`).

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
