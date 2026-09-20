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
```

Run the diagnosis judge as an **in-session sub-agent** (no billed `claude -p`):

1. `python3 distillery/scripts/distiller.py diagnose-negatives <skill> --max-examples 10 --emit-prompt` → `{count, prompt, meta}`. If `count` is 0, stop — no negatives to diagnose.
2. Spawn ONE sub-agent (Agent tool, `general-purpose`) whose entire instruction is the `prompt`; it returns the JSON diagnosis. Write that response to a temp file.
3. `python3 distillery/scripts/distiller.py diagnose-negatives <skill> --max-examples 10 --format-result --response @<file>` → validates against the rubric and prints the report.

The judge classifies each finding under exactly one of seven smallest-failing-decision categories:

| Category | Failure mode | Default edit target |
|---|---|---|
| `wrong_trigger` | Skill fired when not relevant, or didn't fire when it should | `hooks/skill-patterns.sh` regex; SKILL.md `description` |
| `missing_source` | Skill ran but didn't load a reference it needed | Add or expand `references/`; update SKILL.md routing table |
| `skipped_reference` | Reference exists, agent had access, didn't read it | Tighten SKILL.md routing; promote content into SKILL.md |
| `weak_output` | Output format loose or missing structure | Add output template / table format to SKILL.md |
| `missing_validation` | Skill claimed completion without running a check | Add gate to SKILL.md; add validator check if catchable |
| `unsafe_path` | Destructive action without confirmation | Add confirmation requirement; ban destructive verbs |
| `other` | None of the above; only valid with `deferred_reason` | Manual decision |

Present, grouped by category:
- Number of negative sessions analyzed (and how many were relevant to the skill)
- The summary diagnosis
- For each category that has findings: each finding's `smallest_failing_decision` (one sentence), frequency, and either `proposed_edit` (file + change) or `deferred_reason`

If the report includes `schema_violations`, surface them — those are findings the judge emitted that didn't conform to the rubric. Re-run or treat as low-confidence.

### Step 2: Validate findings

For each non-deferred finding, before applying:

1. Read the current skill text at the file referenced by `proposed_edit.file`
2. Verify the change makes sense in context (the diagnosis is based on session data, not the current skill version -- the skill may have already been updated)
3. Check that the proposed change doesn't conflict with other skill sections
4. Confirm the change stays within the skill's token budget (2K-8K chars optimal, 15K max)

Present each validated change for approval. Skip findings that reference content no longer in the skill, and skip any finding whose `proposed_edit.file == "deferred"` -- those are explicitly not for action this round.

### Step 3: Apply approved changes

For each approved finding:
- Edit the file at `proposed_edit.file` using the Edit tool, applying `proposed_edit.change`
- Verify the edit didn't break YAML frontmatter or markdown structure
- If the finding was `wrong_trigger`, also update the corresponding fixture entry in `distillery/tests/fixtures/triggers/<skill>.jsonl` so future regressions catch it
- Append an evidence record to `plugins/whetstone/skills/<skill>/references/evidence/findings-log.md` (create the file with a one-line header if it doesn't exist). The record is one paragraph, not a code block; the schema below is the field set, not a literal template:

  ```markdown
  ## EX-NNN: <short label, ~7 words>

  - Label: negative
  - Kind: <wrong_trigger | missing_source | skipped_reference | weak_output | missing_validation | unsafe_path | other>
  - Origin: human-verified  (the diagnose-negatives reviewer accepted it)
  - Source: <session id or short reproducer>
  - Status: resolved
  - Expected behavior: <one line>
  - Observed behavior: <one line>
  - Skill delta: <file:line and one-line summary; use a sub-bulleted list when the fix touches multiple files>
  - Anonymization: <what was redacted, or "none needed">
  ```

  Pick the next free `EX-NNN` number by scanning the file (or start at `EX-001`). Redact secrets, customer data, and private URLs before writing. The evidence directory is meant for findings that should outlive the current task — for tiny one-off wording fixes, skip the record.

### Step 4: Verify

After applying changes, re-eval via the **in-session sub-agent** path (no billed `claude -p`):

1. `python3 distillery/scripts/distiller.py dspy-eval <skill> --dataset sessions --max-examples 10 --emit-tasks > /tmp/<skill>-tasks.json` → `{count, tasks:[{index, prompt, ...}]}`. Keep the file; step 3 binds verdicts to it.
2. Dispatch one sub-agent per task (Agent tool, parallel, batched ~8); each returns its judge JSON. Collect `[{index, response}]` — one entry per emitted task — into a temp file.
3. `python3 distillery/scripts/distiller.py dspy-eval <skill> --dataset sessions --score-from-verdicts @<file> --manifest @/tmp/<skill>-tasks.json` → binds each verdict to its emitted task (provenance comes from the manifest, not the judge), aggregates the scores, and records the run in `eval-history.jsonl`.

Compare the eval score to the last recorded score in `eval-history.jsonl`. If the score improved or held steady, the changes are validated. If it dropped significantly, review what was changed.

### Step 5: Update metadata

```bash
bash scripts/update-metadata.sh
```

## Notes

- The diagnosis runs as an **in-session sub-agent** via `--emit-prompt` / `--format-result` (Step 1) — no billed `claude -p`, and the judge runs on whatever model the session/sub-agent uses. The direct `diagnose-negatives` path (no `--emit-prompt`) falls back to `claude -p` with `DEFAULT_CLI_MODEL = "opus"`; prefer the sub-agent path.
- Suggestions are based on real user dissatisfaction, not synthetic benchmarks. This makes them high-signal but potentially biased toward the specific projects and tasks in the session history.
- Most common categories observed: `wrong_trigger` (skill too eager / missing exclusions in description), `missing_source` (agent answers without reading the right reference), `weak_output` (no output template, agent improvises shape), `missing_validation` (claims done without checking).
- Post-2026-07-07, a "negative" is a genuine typed user correction only, so they are rare-but-real: a count of 0-3 relevant negatives is now the NORM, and Step 1's "< 3 relevant" caveat is the common case rather than an edge case. When `--emit-prompt` reports `count: 0` it prints a stderr guard and returns `prompt: null` — do NOT dispatch a sub-agent on a null prompt. To inspect historical negatives (from before the skill/pattern last changed or from a retired model), re-run with `--include-stale`; treat those as lower-confidence since they may predate the current skill text.
- The exit code is non-zero (2) if any finding violates the rubric schema. Re-run or open the JSON output to inspect `schema_violations` before treating the report as actionable.
