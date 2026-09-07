---
name: evolve-skill
description: Propose a skill revision and compare fresh executions under a frozen rubric
argument-hint: "<skill-name> [--optimizer gepa|mipro|bootstrap]"
---

# Evolve a skill

Use historical traces to diagnose weaknesses and propose a candidate. Evaluate the candidate by executing the same tasks with both full skill versions and judging the resulting outputs against one unchanged rubric.

## 1. Diagnose and prepare

Run `harvest-sessions`, then `build-golden <skill> --top 20`. Review candidates and label explicit successes `positive`, failures `negative`, and ungraded examples `skip`; run `approve-golden <skill>`.

Optional `dspy-eval <skill> --dataset golden --emit-tasks` assesses recorded outputs retrospectively. Its `--skill-file` changes only the judge rubric. Neither score nor score difference measures how a candidate behaves. Older before/after comparisons using this method are invalid, including those that supplied `--skill-file`.

Before optimization, reserve self-contained comparison cases outside the training and selection data. Each JSONL row requires:

```json
{"case_id":"decimal-sum","task_input":"Return the sum of 17 and 25 as a JSON object with key total. No tools are needed.","acceptance_criteria":"Return exactly {\"total\":42}, with no other text."}
```

Replace this illustrative case with tasks relevant to the skill. Include all necessary source/context in the task or use separately reset, isolated fixtures. Historical prompts lacking their repository state are not executable fixtures. Freeze an independent rubric in a text file before seeing either output. Define correctness, applicable procedure, and conciseness on a 0–10 scale.

## 2. Propose a candidate

```bash
python3 distillery/scripts/distiller.py evolve <skill> --optimizer gepa --iterations 5 --save
```

This step uses paid model calls; follow the user's spending authorization. Keyword fitness is a lexical proxy restricted to positive references or curated `expected_output`, never failed traces. LLM-judge fitness generates single-turn responses, not tool-using execution. Neither proves agentic improvement. Inspect the diff and size constraints; unchanged output is a null result, not proof of Pareto optimality.

## 3. Emit and execute the comparison

```bash
python3 distillery/scripts/distiller.py compare-skill <skill> --emit-tasks \
  --candidate distillery/.eval-data/<skill>/evolved-SKILL.md \
  --dataset /tmp/skill-cases.jsonl --rubric /tmp/skill-rubric.md \
  > /tmp/skill-executions.json
```

The manifest freezes the live baseline, complete candidate, inputs, and rubric. Use `--baseline <file>` if the intended baseline is stored elsewhere.

Dispatch each `tasks[].prompt` to a separate fresh native subagent using the same model and settings. Do not show one execution the other's result. Reset mutable fixtures between executions; do not let concurrent agents edit the same checkout. No CLI model calls are needed for this path.

Collect a JSON array following `execution_contract`: copy `task_id`, `input_sha256`, and `skill_sha256`; add the manifest's `run_id`, actual `executor_id` and `model`, `status` (`completed` or `blocked`), and verbatim `output`. Never substitute historical responses or invent tool evidence. A blocked run leaves the comparison incomplete.

## 4. Judge against the frozen criteria

```bash
python3 distillery/scripts/distiller.py compare-skill <skill> \
  --manifest /tmp/skill-executions.json --outputs /tmp/skill-outputs.json \
  > /tmp/skill-judges.json
```

Dispatch only each judge prompt to a fresh judging subagent. These prompts contain the same rubric and case criteria, plus the corresponding fresh output; candidate instructions cannot redefine success. Collect the `verdict_contract` fields and each judge's JSON as `response`.

```bash
python3 distillery/scripts/distiller.py compare-skill <skill> \
  --manifest /tmp/skill-judges.json --score-from-verdicts /tmp/skill-verdicts.json
```

Execution manifests freeze local skill resources in temporary snapshots: `references/`, `scripts/`, `assets/`, and local Markdown dependencies. Dependencies must remain within the candidate or baseline skill directories; directory links must stay within standard resource directories. Absolute links and escaping symlinks are rejected. Snapshots retain executable permissions and materialize valid local symlinks at their referenced paths. Candidate files outside the installed skill directory inherit missing resource directories from the baseline. Verify this is the intended candidate bundle. Executor prompts name the frozen skill path so relative links resolve; keep these snapshots until collection finishes. Required external resources must be supplied as controlled fixtures or reported blocked. Outputs must copy `bundle_sha256` as well as the other contract fields. The collector rejects modified snapshots, missing/duplicate/mismatched records, blocked executions, mixed execution models, and malformed scores. Report the per-case results and mean paired delta, the number of cases, execution settings, and whether cases were withheld from optimization. Hashes detect accidental record mixing; they do not attest that a caller actually executed an agent. A small paired sample is not a calibrated effect estimate.

## 5. Review and apply

Show the candidate diff, paired results, failures, coverage limits, and size constraints. Do not apply based on a retrospective score delta or a universal numerical threshold. Ask whether to apply the candidate to `plugins/whetstone/skills/<skill>/SKILL.md`; after approval, run the applicable skill and trigger checks. Leave release versions and counts to release time.

For process skills requiring tool use, prefer SkillOpt's existing isolated fixture execution or the native execution path above. Retrospective trace scoring remains useful for diagnosis only.
