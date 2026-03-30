---
name: diagnose-negatives
description: Analyze negative-signal sessions for a skill, identify failure patterns, propose and apply fixes
argument-hint: "<skill-name>"
---

# Diagnose and fix skill failures

Read real negative-signal sessions for a skill, identify recurring failure patterns, and propose targeted skill text edits. This is the practical alternative to automated evolution -- it reads what actually went wrong and fixes the specific gaps.

## Arguments

```
SKILL_NAME=$1  (required)
```

Parse from: `$ARGUMENTS`

If no skill name provided, run `analyze-misfires` first to show which skills have the most issues, then ask which one to diagnose.

## Pipeline

### Step 1: Run diagnosis

```bash
python3 distillery/scripts/distiller.py harvest-sessions
python3 distillery/scripts/distiller.py diagnose-negatives <skill> --max-examples 10
```

Present:
- Number of negative sessions analyzed (and how many were relevant to the skill)
- The summary diagnosis
- Each failure pattern with frequency
- Each suggested change with section, rationale, and proposed text

### Step 2: Validate suggestions

For each suggested change, before applying:

1. Read the current skill text at the referenced section
2. Verify the suggestion makes sense in context (the diagnosis is based on session data, not the current skill version -- the skill may have already been updated)
3. Check that the proposed change doesn't conflict with other skill sections
4. Confirm the change stays within the skill's token budget (2K-8K chars optimal, 15K max)

Present each validated change for approval. Skip suggestions that reference content no longer in the skill.

### Step 3: Apply approved changes

For each approved change:
- Edit the skill's SKILL.md using the Edit tool
- Verify the edit didn't break YAML frontmatter or markdown structure

### Step 4: Verify

After applying changes:

```bash
python3 distillery/scripts/distiller.py dspy-eval <skill> --dataset sessions --max-examples 10
```

Compare the eval score to the last recorded score in `eval-history.jsonl`. If the score improved or held steady, the changes are validated. If it dropped significantly, review what was changed.

### Step 5: Update metadata

```bash
bash scripts/update-metadata.sh
```

## Notes

- The diagnosis uses Sonnet 4.6 via `claude -p` to analyze failure patterns. Cost is ~$0.10-0.15 per run.
- Suggestions are based on real user dissatisfaction, not synthetic benchmarks. This makes them high-signal but potentially biased toward the specific projects and tasks in the session history.
- Common patterns to expect: missing scope gates (skill is too eager), unbounded steps (agent over-reads), vague directives (agent guesses wrong), missing "not for" exclusions in descriptions.
- If the skill has very few relevant negatives (< 3), the diagnosis may be unreliable. Consider running on sessions data instead of golden.
