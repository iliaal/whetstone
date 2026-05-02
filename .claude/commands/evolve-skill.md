---
name: evolve-skill
description: Run the full skill evolution pipeline -- harvest sessions, discover signals, build golden dataset, eval baseline, evolve via DSPy, compare scores
argument-hint: "<skill-name> [--optimizer gepa|mipro|bootstrap]"
---

# Evolve a skill via DSPy optimization

Run the complete skill evolution pipeline for a single skill. Harvests fresh session data, discovers new negative patterns, builds a golden eval dataset, scores the baseline, runs DSPy optimization, and presents a before/after comparison for review.

## Arguments

```
SKILL_NAME=$1  (required: e.g., "code-review", "pinescript", "planning")
OPTIMIZER=$2   (optional: "gepa" (default), "mipro", or "bootstrap")
```

Parse from: `$ARGUMENTS`

If no skill name provided, ask the user which skill to evolve. Show skills with the most harvested data as suggestions.

## Pipeline

Maximize parallelism. Steps within the same group run concurrently (use background subagents or parallel bash). Steps across groups are sequential.

### Group A (parallel): Harvest + Discover

Run these two concurrently:

**Step 1: Harvest sessions (full, all projects)**

```bash
python3 distillery/scripts/distiller.py harvest-sessions
```

Report: total examples harvested, how many attributed to the target skill.

**Step 2: Discover new negative signal patterns**

```bash
python3 distillery/scripts/distiller.py discover-signals --top 20
```

Present the top candidates to the user. If any look like genuine dissatisfaction patterns (not neutral task requests), ask whether to add them to `_NEGATIVE_SIGNAL_PATTERNS` in `distiller.py` before proceeding. If patterns are added, re-run harvest (Step 1) to update signal classifications.

If no new patterns worth adding, continue.

### Group B (sequential): Build golden

Depends on Group A completing.

**Step 3: Build golden eval dataset**

```bash
python3 distillery/scripts/distiller.py build-golden <skill> --top 20 --auto
```

Report: examples selected, positive/negative split, mean quality score.

### Group C (parallel): Eval baseline + Evolve

Run these two concurrently -- both read from the golden dataset, neither writes to the other's output.

**Step 4: Eval baseline**

```bash
python3 distillery/scripts/distiller.py dspy-eval <skill> --dataset golden
```

Record the baseline composite score and per-dimension scores. This is the "before" measurement.

**Step 5: Evolve**

```bash
python3 distillery/scripts/distiller.py evolve <skill> --optimizer <optimizer> --iterations 5 --save
```

If the optimizer produces changes:
- Show the diff
- Report growth percentage and constraint pass/fail
- If constraints fail (>20% growth or >15KB), note the violation

If no changes produced, report that the baseline is already Pareto-optimal for this metric and suggest trying a different optimizer or improving the golden dataset.

### Group D (sequential): Eval evolved + Review

Depends on Group C completing.

**Step 6: Eval evolved (if changed)**

If Step 5 produced an evolved skill and it was saved:

```bash
python3 distillery/scripts/distiller.py dspy-eval <skill> --dataset golden
```

This scores the evolved version. Present a comparison table:

```
| Metric         | Baseline | Evolved | Delta    |
|----------------|----------|---------|----------|
| Composite      | 0.64     | 0.71    | +0.07 (+11%) |
| Correctness    | 7.0      | 7.8     | +0.8     |
| Procedure      | 5.0      | 5.5     | +0.5     |
| Conciseness    | 6.8      | 7.2     | +0.4     |
```

**Step 7: Review and apply**

Present the user with:
1. The diff from Step 5
2. The score comparison from Step 6 (or note if no changes)
3. Constraint status (growth %, size)

Ask: "Apply the evolved skill to `plugins/whetstone/skills/<skill>/SKILL.md`?"

If approved:
- Copy the evolved text to the skill's SKILL.md
- Run `bash scripts/update-metadata.sh`
- Report completion

If rejected, leave everything as-is. The evolved version remains in `.eval-data/<skill>/evolved-SKILL.md` for future reference.

## Notes

- The harvest (Step 1) runs across ALL projects, not just the target skill. This ensures eval data is fresh for everything.
- The evolve step uses OpenRouter (DeepSeek V3.2) for the DSPy optimizer since it needs many fast LLM calls. The eval steps use the default backend (claude-cli / Sonnet 4.6).
- If DSPy is not installed, Step 5 will fail. Install with: `pip install dspy`
- The growth constraint (20%) prevents runaway skill bloat. If the optimizer consistently hits this limit, the skill may need manual editing to make room for improvements.
