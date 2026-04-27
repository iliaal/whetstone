---
name: write-skill
description: Author a new skill from scratch with paired trigger fixtures and full validation. Use when adding a skill that has no upstream skills.sh source (discipline, meta, or internal-pattern skills).
argument-hint: "<skill-name>  (e.g. ia-foo)"
---

# Write Skill

**Skill name:** `$ARGUMENTS`

Scaffold a new plugin skill from scratch, generate paired trigger fixtures, register the regex pattern, and run all gates. For distilling a skill from skills.sh sources, use the `skill-distiller` skill instead — `/write-skill` is for skills with no external upstream.

## Phase 1: Resolve target

1. If `$ARGUMENTS` is empty or doesn't start with `ia-`, ask for the skill name.
2. Validate format: must match `^ia-[a-z0-9][a-z0-9-]*$`, no consecutive hyphens, no banned tokens (`anthropic`, `claude`).
3. Confirm the skill doesn't already exist:
   - `plugins/compound-engineering/skills/<name>/SKILL.md` must NOT exist.
   - `distillery/tests/fixtures/triggers/<name>.jsonl` must NOT exist.
   - No matching `SKILL_PATTERNS[<name>]=` line in `plugins/compound-engineering/hooks/skill-patterns.sh`.
4. Read `CLAUDE.md` "Skill compliance checklist" section to refresh the gates this skill must pass.

## Phase 2: Batch up-front interview

Use `AskUserQuestion` once to collect everything needed before scaffolding. Do not drip-feed questions across turns.

Ask:

1. **Class** — one of the five values from `CLAUDE.md` "Skill class taxonomy": `language`, `discipline`, `workflow`, `meta`, `tool`. Read that section before asking so the option descriptions match what the validator will accept.
2. **Scope summary** — one or two sentences: what this skill is for, when it fires.
3. **Primary trigger vocabulary** — 3-6 distinctive phrases users would type.
4. **Existing skills it should not overlap with** — names of any close-in-scope `ia-*` skills the user already has in mind.

## Phase 3: Inspect prior art

Read the SKILL.md of every skill the user named in question 4 (and any others that look similar by class). Goals:

- Match house style (frontmatter shape, body voice, references/ patterns).
- Identify trigger overlap risk — `validate-plugin` will flag descriptions with >70% word overlap.
- Find a close structural template to model the new skill after.

## Phase 4: Scaffold

Generate four artifacts atomically. Do not split across phases.

### 4a. SKILL.md

Path: `plugins/compound-engineering/skills/<name>/SKILL.md`

Frontmatter rules (all hard requirements — `validate-plugin` enforces them):

- `name:` matches the directory name exactly.
- `class:` one of `language`, `discipline`, `workflow`, `meta`, `tool` (the value from question 1). Required. The validator rejects unknown values.
- `description:` describes **what + when**, not how. Lead with one sentence on what the skill does, then `Use when ...` with concrete trigger language. Stay under 80 tokens. No vague phrases (`comprehensive`, `best practices`, `robust`, `seamless`, `powerful` — see `_VAGUE_DESCRIPTION_PHRASES` in `distillery/scripts/distiller.py`). No second person, no provider names unless the skill is intentionally provider-specific.
- No inert fields (`triggers`, `role`, `scope`, `domain`, `version`, `tags` — they're ignored by Claude Code).

Body rules:

- Imperative voice (verb-first instructions).
- 100-2000 tokens ideal, 4000 hard cap. Split to `references/` if larger.
- No machine-specific paths (`/home/...`, `/Users/...`, `~/ai/...`, `C:\Users\...`). Use `<repo-root>` or `<skill-dir>` placeholders.
- No placeholder text (`TODO`, `FIXME`, `XXX`, `[YOUR ...]`).
- No MUST/ALWAYS/NEVER spam (>15 directives is flagged as OVER_CONSTRAINED).
- If creating `references/`, link every file with `[name](./references/name.md)` syntax — orphans are flagged. Each reference under 150 lines (warning) and 800 lines (error).
- **Skill Independence**: do not instruct the agent to invoke another skill by name. Forms to avoid: `run the ia-X skill`, `use the \`ia-X\` skill`, `hand off to ia-X`, `<vendor>:Y` runtime references. Other skills may be missing, renamed, or user-overridden — name-invocation silently breaks in all three cases. Instead, state the intent directly (`If on \`main\`, create a feature branch first.`) and trust skill discovery to surface the right skill, or load a local file via `[name](./references/name.md)`. Naming an agent (Agent tool dispatch) or referencing a skill in non-runtime prose (provenance, audit allowlist) is fine.

### 4b. Trigger fixtures

Path: `distillery/tests/fixtures/triggers/<name>.jsonl`

JSONL format. **Required floors: 5 should_trigger AND 5 should_not_trigger** — `test-triggers` fails the run if either count is below floor.

```json
{"prompt": "<realistic phrasing a user would type>", "expect": true, "added_in": "<current-version>", "source": "initial"}
{"prompt": "<adjacent task that must NOT trigger this skill>", "expect": false, "added_in": "<current-version>", "source": "initial"}
```

Drafting guidance:

- Positives: 5+ phrasings that exercise different ways a user might invoke this skill. Vary verb, vary scope, include at least one terse phrasing.
- Negatives: 5+ phrasings that look superficially related but should not trigger. Include phrasings that match adjacent skills' descriptions (the `validate-plugin` DUPLICATE_TRIGGER detector catches this kind of overlap).
- Do not use AI-flavored placeholders. Each prompt should be a thing a real user would type.

Read the current plugin version from `plugins/compound-engineering/.claude-plugin/plugin.json` for the `added_in` field.

### 4c. SPEC.md (maintenance contract)

Path: `plugins/compound-engineering/skills/<name>/SPEC.md`

Seven required headings (the validator rejects missing ones as HIGH):

```markdown
# <name> Specification

## Intent
<one paragraph: what this skill exists for, primary purpose, class context>

## Scope
In scope:
- <bullets pulled from SKILL.md routing>
Out of scope:
- <adjacent skills that should not overlap>

## Trigger Context
- Class: <one of language, discipline, workflow, meta, tool>
- Hook regex: SKILL_PATTERNS[<name>]
- Common requests: <3 should_trigger samples>
- Should not trigger for: <3 should_not_trigger samples>

## Source And Evidence Model
<canonical sources, data-not-stored rules, coverage matrix>

## Evaluation
<lightweight + deeper command snippets, acceptance gates>

## Known Limitations
<placeholder; fill in over time as drift surfaces>

## Maintenance Notes
<when each artifact must be updated>
```

For an existing filled example to model after, read any `plugins/compound-engineering/skills/ia-*/SPEC.md`. To auto-generate a starter SPEC.md from the SKILL.md and fixture pair, run `python3 scripts/generate-spec.py` (it skips skills that already have SPEC.md, so it's safe to re-run).

File-relationship matrix — what each artifact owns (don't duplicate across files):

| File | Purpose |
|---|---|
| `SKILL.md` | Runtime activation and execution instructions loaded by agents. |
| `SPEC.md` | Maintenance contract for humans and agents improving the skill. |
| `SOURCES.md` | Source inventory, decisions, coverage matrix, gaps, changelog (optional). |
| `references/` | Runtime-loadable domain/process detail. |
| `references/evidence/` | Persistent positive/negative iteration examples. |

SPEC.md design rules (apply when filling the template):

1. Describe intent and maintenance contract; do not add runtime instructions that belong in SKILL.md.
2. Summarize source categories and link to SOURCES.md (if present) — do not duplicate full source tables.
3. Describe evidence classes and storage policy; keep raw examples in `references/evidence/`.
4. Include out-of-scope behavior and known limitations so future edits do not expand the skill accidentally.
5. Include evaluation expectations that explain what "good" means; link to runnable prompts rather than duplicating them.
6. Keep private or sensitive evidence redacted; store only what is needed to reproduce and improve behavior.

SPEC.md must not contain machine-specific paths, secrets, or unredacted personal data. The same `MACHINE_PATH_LEAK` gate that scans SKILL.md and references applies here.

### 4d. SOURCES.md (optional source-provenance ledger)

Path: `plugins/compound-engineering/skills/<name>/SOURCES.md`

Recommended for skills synthesized from external repos, marketplace skills, a mixed source pack, or any skill that accumulates persistent iteration evidence under `references/evidence/` — anything where future maintainers will need to know *what shaped this skill*. Skip for skills authored from scratch with no external source pack and no evidence ledger (the SPEC.md "Source And Evidence Model" section already covers them).

Three sections:

1. **Source inventory** — markdown table: `| Source | Type | Trust tier | Retrieved | Confidence | Contribution | Usage constraints | Notes |`. Trust tiers: `canonical` (official spec, repo CLAUDE.md, owner-blessed) > `secondary` (well-regarded blog post, prior-art pattern). Avoid scraping low-tier content.
2. **Decisions** — numbered list of synthesis decisions and the constraint that drove each (e.g., "Path guidance avoids host-specific absolutes because plugin is mirrored to ai-skills"). One line per decision.
3. **Changelog** — date-stamped entries for source additions, scope changes, or rule reversals.

Keep SOURCES.md ledger-style. Do not duplicate runtime content from SKILL.md or maintenance contract content from SPEC.md.

If iteration evidence (positive/negative examples, holdout set) accumulates, store it under `references/evidence/EX-NNN.md` instead of in SOURCES.md — see `/diagnose-negatives` for the schema.

### 4e. Hook regex pattern

Append to `plugins/compound-engineering/hooks/skill-patterns.sh`:

```bash
SKILL_PATTERNS[<name>]='<regex>'
SKILL_TIERS[<name>]=<1|2|3>
```

Tier guide: 1 = high precision / always-relevant (`debugging`, `code-review`); 2 = stack-specific (`tailwind`, `pinescript`); 3 = niche or workflow (`compound-docs`, `file-todos`).

Build the regex from the trigger vocabulary in question 3. Test it locally first:

```bash
python3 distillery/scripts/distiller.py eval-triggers <name> \
  --pattern '<regex>' \
  --queries '<JSON array of all positives>' \
  --negatives '<JSON array of all negatives>'
```

Iterate until F1 = 1.0 across the fixture set, then commit the pattern to `skill-patterns.sh`.

## Phase 5: Run all gates

Run these in order. Stop at the first failure and fix before continuing.

```bash
# 1. Plugin-wide validator scoped to the new component
#    (catches frontmatter, body size, overlap, dead refs, machine paths, ref bloat)
python3 distillery/scripts/distiller.py validate-plugin --component <name>

# 2. Trigger regression (enforces 5+5 floor and F1 = 1.0)
python3 distillery/scripts/distiller.py test-triggers --skill <name>

# 3. Re-run validate-plugin without --component to confirm no DUPLICATE_TRIGGER
#    or count-mismatch findings appear at the fleet level
python3 distillery/scripts/distiller.py validate-plugin

# 4. Update the manifest so staleness filtering knows about the new skill
python3 scripts/generate-manifest.py
```

Do not run `update-metadata.sh`, `mirror-to-ai-skills.sh`, or any release scripts — those are owned by `/release`.

## Phase 6: Report

Output four sections in this order:

1. **Summary** — one line on what was created (skill name, class, trigger pattern).
2. **Changes Made** — bulleted list of files created/modified with line counts.
3. **Validation Results** — verbatim output of each gate above (PASS/FAIL with metrics).
4. **Open Gaps** — anything the skill needs that this command did not cover (e.g., `references/` content, integration tests, semantic injection fixture in `tests/fixtures/semantic-triggers.jsonl`).

If validation surfaces fixable issues mid-flight (e.g., an overly-broad regex catching a negative case), fix and re-run rather than reporting failure. Reject completion if any HIGH-severity finding remains in `validate-plugin --component <name>` or if `test-triggers --skill <name>` fails.

Run `ia-verification-before-completion` before reporting done.

## Success criteria

- New skill directory exists with valid SKILL.md.
- Trigger fixture has at least 5 positives and 5 negatives, F1 = 1.0.
- Hook pattern registered and matches the fixture set.
- `validate-plugin --component <name>` returns no HIGH findings.
- Manifest updated.
- No version bumps, README edits, or CHANGELOG entries (those belong to `/release`).
