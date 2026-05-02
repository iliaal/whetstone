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
=== postgresql (51% misfire) ===
Current regex: SKILL_PATTERNS[postgresql]='postgres|jsonb|rls|cte[s]?|window\.?function'
Problem: "postgres" matches any mention of PostgreSQL in task context, including Laravel tasks that reference a postgres database
Proposed regex: SKILL_PATTERNS[postgresql]='postgres.*(?:query|schema|index|optim)|jsonb|rls|\bcte[s]?\b|window\.?function|explain\s+analyze'
Description change: Add "Not for tasks that merely use PostgreSQL as a backend"
```

### Step 4: Apply approved changes

For each approved change:
- Edit `plugins/whetstone/hooks/skill-patterns.sh` with the new regex
- Edit the skill's SKILL.md description if a description change was approved
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
- Regex changes affect all future sessions. Test changes with `distiller.py eval-triggers` before committing.
- Some misfire is acceptable -- skills like `ia-debugging` (19%) are broadly useful even when not the primary task. Focus on skills above 30%.
