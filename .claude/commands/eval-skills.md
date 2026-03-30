---
name: eval-skills
description: Eval all skills with sufficient data, rank by composite score, identify candidates for optimization
argument-hint: "[--min-examples 10] [--top 10]"
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

Present a table:
```
| Skill                          | Examples | Positive | Negative |
|--------------------------------|----------|----------|----------|
| code-review                    |      163 |      110 |       53 |
| ...                            |          |          |          |
```

### Step 3: Eval each eligible skill (parallel)

For each eligible skill, run eval in parallel using background subagents (one per skill):

```bash
python3 distillery/scripts/distiller.py build-golden <skill> --top 20 --auto
python3 distillery/scripts/distiller.py dspy-eval <skill> --dataset golden --max-examples 10
```

Use the default backend (claude-cli / Sonnet 4.6). Cap at 10 examples per skill to control cost and time.

### Step 4: Rank and present

Collect all eval results. Present a ranked table sorted by composite score (lowest first):

```
| Rank | Skill                     | Composite | Correct | Procedure | Concise | Examples | Signal |
|------|---------------------------|-----------|---------|-----------|---------|----------|--------|
|    1 | pinescript                |     0.42  |    4.2  |      5.0  |    5.1  |       92 |  61% + |
|    2 | receiving-code-review     |     0.48  |    5.1  |      5.0  |    4.8  |       56 |  34% + |
|    3 | simplifying-code          |     0.51  |    5.5  |      5.0  |    5.3  |       69 |  54% + |
|  ... |                           |           |         |           |         |          |        |
```

"Signal" column shows positive rate from harvest data (lower = more user dissatisfaction).

### Step 5: Recommendations

Flag the bottom `TOP` skills and recommend action:

- **Composite < 0.4**: Strong candidate for `/evolve-skill` -- skill is underperforming
- **Composite 0.4-0.5**: Worth investigating -- check if low score is due to irrelevant injection or genuine skill weakness
- **Composite 0.5-0.6**: Marginal -- may benefit from manual review more than automated evolution
- **Composite > 0.6**: Performing well -- deprioritize unless negative signal rate is high

Cross-reference composite score with harvest signal rate. A skill with high composite but low positive rate suggests the eval data itself may need better curation (golden dataset review). A skill with low composite AND low positive rate is the strongest optimization candidate.

Present final recommendation:
```
Recommended for /evolve-skill (lowest composite + highest negative rate):
  1. pinescript (composite: 0.42, 39% negative)
  2. receiving-code-review (composite: 0.48, 66% negative)
  3. ...
```

## Notes

- This command can take 5-15 minutes depending on how many skills have data, since each eval makes LLM calls.
- Eval history is automatically saved per-skill, so running this periodically builds a trend over time.
- Skills with fewer than MIN_EXAMPLES (default 30) are skipped -- below that threshold, scores are dominated by outliers and don't represent real skill effectiveness.
- The parallel eval step should use background subagents to maximize throughput. Each subagent runs build-golden + dspy-eval for one skill.
