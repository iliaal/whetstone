---
name: analyze-misfires
description: Identify skills injected where not needed, propose regex and description tightening
argument-hint: "[--min-examples 30] [--top 5]"
---

# Analyze skill injection misfires

Identify skills whose trigger regex matches too broadly, causing injection into irrelevant tasks. Propose concrete fixes to `skill-patterns.sh` and skill descriptions.

## Arguments

```
MIN_EXAMPLES=30  (default)
TOP=5            (how many worst misfires to investigate, default: 5)
```

Parse from: `$ARGUMENTS`

## Pipeline

### Step 1: Harvest + analyze

```bash
python3 distillery/scripts/distiller.py harvest-sessions
python3 distillery/scripts/distiller.py analyze-misfires --min-examples <MIN_EXAMPLES>
```

Present the full misfire table. Flag skills with misfire rate > 15%.

### Step 2: Investigate top misfires

For each of the top `TOP` misfiring skills:

1. Read the current regex from `plugins/whetstone/hooks/skill-patterns.sh` (grep for `SKILL_PATTERNS[<skill-name>]`)
2. Read the skill's YAML description from its SKILL.md
3. Review the irrelevant task samples from the analyze-misfires output
4. Identify what the regex is matching that it shouldn't (e.g., "database" matching audit tasks that mention databases)

### Step 3: Propose fixes

For each misfiring skill, propose:

1. **Tightened regex** -- remove overly broad terms, add word boundaries, require more specific combinations
2. **Description update** -- add explicit "not for X" exclusions if the description is attracting wrong matches
3. **Tier adjustment** -- if the skill is Tier 1 but shouldn't fire as eagerly, suggest moving to Tier 2

Present each proposed change for review before applying. Format:

```
=== ia-postgresql (51% misfire) ===
Current regex: SKILL_PATTERNS[ia-postgresql]='postgres|jsonb|rls|cte[s]?|window\.?function'
Problem: "postgres" matches any mention of PostgreSQL in task context, including Laravel tasks that reference a postgres database
Proposed regex: SKILL_PATTERNS[ia-postgresql]='postgres.*(?:query|schema|index|optim)|jsonb|rls|\bcte[s]?\b|window\.?function|explain\s+analyze'
Description change: Add "Not for tasks that merely use PostgreSQL as a backend"
```

### Step 4: Apply approved changes

For each approved change:
- Edit `plugins/whetstone/hooks/skill-patterns.sh` with the new regex
- Edit the skill's SKILL.md description if a description change was approved
- **Append regression fixtures** (CLAUDE.md mandate — every pattern change needs one): add the misfiring task samples as `should_not_trigger` cases, plus a couple of genuine-use `should_trigger` cases, to `distillery/tests/fixtures/triggers/<ia-name>.jsonl`. This is what stops the tightened regex from silently regressing later.
- Run `bash scripts/update-metadata.sh`

### Step 5: Verify

After applying changes, re-run analyze-misfires to confirm misfire rates dropped:

```bash
python3 distillery/scripts/distiller.py harvest-sessions
python3 distillery/scripts/distiller.py analyze-misfires
```

Compare before/after misfire rates for the changed skills.

## Notes

- The relevance check uses keyword overlap, which is imperfect. A skill with 0% misfire but keyword overlap of 100% might still be injected into irrelevant tasks if the keywords are too generic. Use the irrelevant task samples to verify.
- Regex changes affect all future sessions. Iterate on a candidate regex with `eval-triggers` (fast, no fixture file needed), then lock it in with the regression gate `test-triggers`:

  ```bash
  # iterate: test a candidate pattern against inline queries
  python3 distillery/scripts/distiller.py eval-triggers <ia-name> \
    --pattern '<regex>' \
    --queries '{"should_trigger":["real use 1","real use 2"],"should_not_trigger":["misfire 1","misfire 2"]}'
  # regression gate: runs the committed fixtures (a /release + /audit-plugin gate)
  python3 distillery/scripts/distiller.py test-triggers --skill <ia-name>
  ```

  Always pass the full `ia-` prefixed name. `test-triggers --skill <name>` exits 2 if the name matches no fixture file, so `--skill debugging` fails where `--skill ia-debugging` runs.
- Some misfire is acceptable -- broadly-useful skills fire on adjacent tasks by design. Compare each skill's live rate from the current `analyze-misfires` output against the command's 30% action threshold rather than any hardcoded figure (e.g. `ia-debugging` has run well above 30% at times and is still expected to be broad); focus effort on skills over the threshold whose samples are genuinely off-topic.
- The 2026-07-07 attribution fix removed a ~10x inflation (each session was previously counted once per skill in its injected list, not once per owner). Injected counts are now unique sessions per owner skill, so `--min-examples` filters on real session volume — a threshold of 30 today is far stricter than the same number was pre-fix.
