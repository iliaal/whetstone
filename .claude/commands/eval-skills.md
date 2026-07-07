---
name: eval-skills
description: Eval all skills with sufficient data, rank by composite score, identify candidates for optimization
argument-hint: "[--min-examples 30] [--top 10]"
---

# Evaluate and rank all skills

Score every skill that has sufficient harvested eval data, rank them by composite score, and identify the best candidates for `/evolve-skill`.

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

Collect all eval results. Present a ranked table sorted by composite score (lowest first):

```
| Rank | Skill                     | Composite | Correct | Procedure | Concise | Examples | Neg | Amb |
|------|---------------------------|-----------|---------|-----------|---------|----------|-----|-----|
|    1 | ia-pinescript             |     0.42  |    4.2  |      5.0  |    5.1  |       92 |   4 |  85 |
|    2 | ia-receiving-code-review  |     0.48  |    5.1  |      5.0  |    4.8  |       56 |   2 |  51 |
|    3 | ia-simplifying-code       |     0.51  |    5.5  |      5.0  |    5.3  |       69 |   1 |  63 |
|  ... |                           |           |         |           |         |          |     |     |
```

The last two columns are absolute COUNTS, not rates. **Neg** = genuine typed user corrections (rank by this — a raw count of 2-4 is meaningful and actionable). **Amb** = examples with no typed outcome (the normal case; not a dissatisfaction signal). Do not compute a "positive rate": with positives near zero and ambiguous dominating, a rate is noise.

### Step 5: Recommendations

Flag the bottom `TOP` skills and recommend action:

- **Composite < 0.4**: Strong candidate for `/evolve-skill` -- skill is underperforming
- **Composite 0.4-0.5**: Worth investigating -- check if low score is due to irrelevant injection or genuine skill weakness
- **Composite 0.5-0.6**: Marginal -- may benefit from manual review more than automated evolution
- **Composite > 0.6**: Performing well -- deprioritize unless it carries genuine negative examples

Rank primarily by composite (lowest first), then break ties and prioritize by absolute **negative count** — each negative is a real typed user correction and is directly actionable via `/diagnose-negatives`. A skill with low composite AND one or more negatives is the strongest candidate. Do NOT rank by positive/negative *rate*: with ambiguous dominating, rates are dominated by the no-typed-outcome class and are not a quality signal.

Present final recommendation:
```
Recommended for /evolve-skill or /diagnose-negatives (lowest composite, most negatives):
  1. ia-pinescript (composite: 0.42, 4 negatives)
  2. ia-receiving-code-review (composite: 0.48, 2 negatives)
  3. ...
```

## Notes

- This command can take 5-15 minutes depending on how many skills have data, since each eval dispatches judge sub-agents.
- Eval history is automatically saved per-skill, so running this periodically builds a trend over time.
- Skills with fewer than MIN_EXAMPLES (default 30) are skipped -- below that threshold, scores are dominated by outliers and don't represent real skill effectiveness.
- The orchestrator runs `build-golden`/`approve-golden` then `dspy-eval --emit-tasks` per skill (deterministic, no LLM), and the emitted judge tasks are what fan out to sub-agents. Each sub-agent judges ONE emitted task and returns its JSON verdict; the orchestrator aggregates them with `--score-from-verdicts`. A sub-agent does not run `build-golden` or `dspy-eval` itself.
