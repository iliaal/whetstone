---
name: eval-skills
description: Eval all skills with sufficient data, rank by procedure-following score, identify candidates for optimization
argument-hint: "[--min-examples 30] [--top 10]"
---

# Evaluate and rank all skills

Score every skill that has sufficient harvested eval data, rank them by procedure-following score, and identify the best candidates for `/evolve-skill`.

## Arguments

```
MIN_EXAMPLES=30  (minimum harvested examples to include a skill, default: 30)
TOP=10           (how many bottom-ranked skills to highlight, default: 10)
```

Parse from: `$ARGUMENTS`

## Pipeline

### Step 1: Harvest fresh data

```bash
python3 distillery/scripts/distiller.py harvest-sessions
```

Capture the JSON output. Extract the `skills` dict to know which skills have data and how many examples each has.

### Step 2: Identify eligible skills

From the harvest output, list skills with `count >= MIN_EXAMPLES`. Exclude `_unattributed`. Sort by example count descending.

Present a table (include the `ambiguous` count — it is the dominant class post-2026-07-07 and the split is meaningless without it):
```
| Skill                          | Examples | Positive | Negative | Ambiguous |
|--------------------------------|----------|----------|----------|-----------|
| ia-code-review                 |      438 |        0 |        3 |       435 |
| ...                            |          |          |          |           |
```

Read the columns honestly:
- **ambiguous** — no typed user outcome. This is the NORMAL case for subagent sessions (they end without a human reply), so a high ambiguous count is expected, not a problem.
- **positive** — requires 2+ typed user messages with satisfaction signal; rare for subagent-driven skills.
- **negative** — a genuine typed user correction. Low counts (0-3) are the norm now; each one is high-signal.

### Step 3: Eval each eligible skill (in-session sub-agents)

The judging runs as **in-session sub-agents** (no billed `claude -p`). For each eligible skill, build a golden set then emit judge tasks.

RECOMMENDED (human-label) build, since harvest data is mostly `ambiguous` and `approve-golden` hard-errors on ungraded labels:

```bash
python3 distillery/scripts/distiller.py build-golden <skill> --top 20
# → edit candidates.jsonl labels to positive / negative / skip, then:
python3 distillery/scripts/distiller.py approve-golden <skill>
python3 distillery/scripts/distiller.py dspy-eval <skill> --dataset golden --max-examples 10 --emit-tasks
```

Fast path (only when the harvested signal is already well-graded): swap the first two commands for `build-golden <skill> --top 20 --auto`. `--auto` prints a stderr WARNING when >50% of rows are `ambiguous`; if you see it, fall back to the human-label path — an ambiguous-dominated golden set produces meaningless eval scores.

The `--emit-tasks` call returns `{count, tasks:[{index, prompt, ...}]}` with no LLM call. Then:

1. Dispatch one sub-agent (Agent tool, `general-purpose`) per task — each task's `prompt` is the full judge prompt; the sub-agent returns ONLY its judge JSON. Batch ~8 per message.
2. Collect `[{index, signal, session_id, skill_version, response}]` and aggregate: `python3 distillery/scripts/distiller.py dspy-eval <skill> --dataset golden --score-from-verdicts @<file>`.

Cap at 10 examples per skill. **Mind session rate limits:** across all eligible skills this is many sub-agents — pace the batches rather than firing every skill's tasks at once.

### Step 4: Rank and present

Collect all eval results. Present a ranked table sorted by procedure-following score (lowest first). Keep the composite column for continuity with saved history, but do not rank on it:

```
| Rank | Skill                     | Composite | Correct | Procedure | Concise | Examples | Neg | Amb |
|------|---------------------------|-----------|---------|-----------|---------|----------|-----|-----|
|    1 | ia-pinescript             |     0.42  |    4.2  |      5.0  |    5.1  |       92 |   4 |  85 |
|    2 | ia-receiving-code-review  |     0.48  |    5.1  |      5.0  |    4.8  |       56 |   2 |  51 |
|    3 | ia-simplifying-code       |     0.51  |    5.5  |      5.0  |    5.3  |       69 |   1 |  63 |
|  ... |                           |           |         |           |         |          |     |     |
```

The last two columns are absolute COUNTS, not rates. **Neg** = genuine typed user corrections (the tie-breaker — a raw count of 2-4 is meaningful and actionable). **Amb** = examples with no typed outcome (the normal case; not a dissatisfaction signal). Do not compute a "positive rate": with positives near zero and ambiguous dominating, a rate is noise.

### Step 5: Recommendations

Flag the bottom `TOP` skills and recommend action.

**Rank by `procedure_following`, not by composite.** The composite is
`0.5*correctness + 0.3*procedure + 0.2*conciseness` (`distiller.py`), and only the
procedure axis measures what a skill claims to change. Correctness is mostly a
property of the model and the task; conciseness moves with the ambient output
style. Fusing the three hides the signal inside two axes the skill does not
control, so a skill that improved procedure at a small cost in conciseness looks
flat. Report all three axes and rank on procedure.

- **Procedure < 4.0**: Strong candidate for `/evolve-skill` -- the agent had the skill and did not follow it
- **Procedure 4.0-5.0**: Read the judge notes before acting. 5.0 is the judge's "skill not applicable" default, so a cluster at exactly 5.0 is a *trigger* problem for `/analyze-misfires`, not a content problem
- **Procedure 5.0-7.0**: Marginal -- manual review beats automated evolution
- **Procedure > 7.0**: Performing well -- deprioritize unless it carries genuine negative examples

Break ties by absolute **negative count** — each negative is a real typed user correction and is directly actionable via `/diagnose-negatives`. A skill with low procedure AND one or more negatives is the strongest candidate. Do NOT rank by positive/negative *rate*: with ambiguous dominating, rates are dominated by the no-typed-outcome class and are not a quality signal.

Every score here is absolute with no reference point: nothing in this pipeline compares the skill against no skill at all, so a number cannot tell you whether the skill beats an empty prompt. Read these as "which skills to look at first", never as "this skill earns its injection cost".

Present final recommendation:
```
Recommended for /evolve-skill or /diagnose-negatives (lowest procedure, most negatives):
  1. ia-pinescript            (proc 5.0, corr 4.2, conc 5.1, 4 negatives)
  2. ia-receiving-code-review (proc 5.0, corr 5.1, conc 4.8, 2 negatives)
  3. ...
```

When several skills sit at exactly 5.0 procedure, say so and route them to `/analyze-misfires` first — that is the judge reporting "not applicable", which means the trigger fired on the wrong task, and evolving the body cannot fix a targeting problem.

## Notes

- This command can take 5-15 minutes depending on how many skills have data, since each eval dispatches judge sub-agents.
- Eval history is automatically saved per-skill, so running this periodically builds a trend over time.
- Skills with fewer than MIN_EXAMPLES (default 30) are skipped -- below that threshold, scores are dominated by outliers and don't represent real skill effectiveness.
- The orchestrator runs `build-golden`/`approve-golden` then `dspy-eval --emit-tasks` per skill (deterministic, no LLM), and the emitted judge tasks are what fan out to sub-agents. Each sub-agent judges ONE emitted task and returns its JSON verdict; the orchestrator aggregates them with `--score-from-verdicts`. A sub-agent does not run `build-golden` or `dspy-eval` itself.
