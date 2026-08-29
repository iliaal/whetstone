# ia-verification-before-completion Specification

## Intent

`ia-verification-before-completion` is a `discipline`-class skill (an engineering practice not tied to one stack). It requires fresh, claim-matched evidence, rejects weakened proof and proof-class inflation, and keeps partial or refusal-only behavior visibly incomplete without imposing a fixed report template.

## Scope

In scope:
- Behaviors described in `SKILL.md` and routed via the should_trigger phrasings in `distillery/tests/fixtures/triggers/ia-verification-before-completion.jsonl`.
- Updates to runtime behavior, structure, trigger precision, references, and validation.

Out of scope:
- Acting as the runtime instructions themselves (those live in `SKILL.md`).
- Trigger phrasings already covered by adjacent `ia-*` skills (`validate-plugin` flags >70% description overlap as DUPLICATE_TRIGGER).
- <!-- to fill in: domain-specific exclusions when the skill drifts -->

## Trigger Context

- Class: `discipline`
- Hook regex: `plugins/whetstone/hooks/skill-patterns.sh` -> `SKILL_PATTERNS[ia-verification-before-completion]`
- Common requests (from fixture should_trigger):
  - "verify before pushing the release branch"
  - "verify that tests pass before committing"
  - "about to mark this done -- verify first"
- Should not trigger for (from fixture should_not_trigger):
  - "write a new middleware for rate limiting"
  - "refactor the payment gateway integration"
  - "I'm confident the refactor didn't break anything"

## Source And Evidence Model

Authoritative sources:

- `SKILL.md` -- runtime instructions and reference routing.
- `references/*.md` -- bundled supplementary content (1 file(s)).
- `distillery/tests/fixtures/triggers/ia-verification-before-completion.jsonl` -- positive and negative trigger phrasings under regression test.
- `plugins/whetstone/hooks/skill-patterns.sh` -- regex pattern that fires this skill.
- `distillery/.eval-data/ia-verification-before-completion/` -- harvested session examples (when present).

Data that must not be stored in this skill or its references:

- Secrets, credentials, tokens.
- Machine-specific filesystem paths (`/home/...`, `/Users/...`, `~/ai/...`). The validator (`MACHINE_PATH_LEAK`) flags these as HIGH.
- Private URLs, customer data, or unredacted personal information.

### Coverage matrix

| Dimension | Status | Evidence |
|---|---|---|
| Trigger fixtures | complete | distillery/tests/fixtures/triggers/ia-verification-before-completion.jsonl (>=5 should_trigger, >=5 should_not_trigger) |
| Hook regex pattern | complete | plugins/whetstone/hooks/skill-patterns.sh (`SKILL_PATTERNS[ia-verification-before-completion]`) |
| Reference architecture | complete | 1 file(s) under references/ |
| Proof integrity and honest completion | complete | `SKILL.md` The Rule, Red Flags, and Completion Reporting |
| Real-usage signal | <!-- populated by harvest-sessions when sessions exist --> | distillery/.eval-data/ia-verification-before-completion/ (created by harvest-sessions) |

## Evaluation

Lightweight (run on every change):

```bash
python3 distillery/scripts/distiller.py validate-plugin --component ia-verification-before-completion
python3 distillery/scripts/distiller.py test-triggers --skill ia-verification-before-completion
```

Deeper (when behavior risk warrants):

```bash
python3 distillery/scripts/distiller.py dspy-eval ia-verification-before-completion
python3 distillery/scripts/distiller.py diagnose-negatives ia-verification-before-completion
```

Acceptance gates:
- `validate-plugin --component ia-verification-before-completion` returns 0 HIGH findings.
- `test-triggers --skill ia-verification-before-completion` returns F1 = 1.0 with floors of 5 should_trigger and 5 should_not_trigger.
- For dspy-eval, the composite score does not regress against the most recent saved baseline (see `distillery/.eval-data/ia-verification-before-completion/history.json`).

## Known Limitations

- Whether evidence is genuinely live can depend on repository-specific runtime boundaries that this portable skill cannot infer.
- Scope confirmation remains judgment-based; inspection should resolve safe defaults, while material ambiguity still requires user input.

## Maintenance Notes

- Update `SKILL.md` when the runtime workflow, branch conditions, or output contract changes.
- Update this `SPEC.md` when intent, scope, evidence model, evaluation gates, or maintenance expectations change.
- Update the trigger fixture when adding new positive phrasings, removing stale ones, or expanding scope (the 5/5 floor is a hard validator gate).
- Update the hook regex in `skill-patterns.sh` whenever fixture positives expose a missed phrasing; verify F1 = 1.0 with `eval-triggers` before committing.
- Run the full release pipeline via `/release` -- never bump versions or update CHANGELOG.md from a per-skill edit.
