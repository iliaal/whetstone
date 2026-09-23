# distillery/skillopt

A validation-gated optimizer for Whetstone **process** skills, built on a
vendored, trimmed [microsoft/SkillOpt](https://github.com/microsoft/SkillOpt)
(MIT; see [VENDORED.md](./VENDORED.md)). It tunes a `SKILL.md` by running the
target model **agentically** against tasks and scoring each rollout. A skill
edit is accepted only when it improves a held-out validation split, and the
result is written as a deployable `best_skill.md`.

This is offline tooling: it does not ship in the plugin, is not mirrored to
ai-skills, and is not part of the release pipeline. It complements the
DSPy-based `evolve` (`distillery/scripts/distiller.py evolve`); see
[How this differs from `evolve`](#how-this-differs-from-evolve).

## How it works

SkillOpt's trainer (`skillopt/engine/trainer.py`, vendored, untouched) runs a
training-style loop: epoch → rollout → reflect → aggregate → LR-clipped edit →
**validation gate** → (optional) slow-update / meta-skill. Everything
task-specific lives in one pluggable *environment*; ours is
`skillopt/envs/whetstone/`.

The pilot environment optimizes **ia-debugging** against curated seeded-bug
fixtures, with a **hybrid reward**:

- **`hard` (0/1)**: deterministic. After the rollout, the evaluator restores the
  fixture's *pristine* test (so a weakened test can't pass) and runs it in the
  workspace. Bug fixed → 1.
- **`soft` (0–1)**: a per-skill process rubric (`skillopt/envs/whetstone/rubric.py`)
  judged by the optimizer model on the rollout trajectory. `score_criteria`
  zeroes, in code, any criterion whose evidence does not share a contiguous run
  with the trajectory. The trajectory is the target's tool-use transcript plus
  **harness-verified artifacts**: the real pre/post pytest runs and a
  harness-computed diff of the agent's edits. The transcript is the full ordered
  stream (Read/Bash/Edit events) only when the rollout runs nested in a Claude
  Code session (`CLAUDE_CODE_COORDINATOR_MODE=1`); standalone,
  `--output-format text` returns only the final message. The harness artifacts
  are therefore the ground truth that is always present: outcome criteria ground
  either way, temporal criteria need the stream. The matcher un-escapes
  stream-json (`\n`, `\"`) before comparing, or verbatim quotes would miss.

  > **soft gates only when enabled.** The vendored validation gate selects on
  > `compute_score`, which is mean `hard` unless `SKILLOPT_SOFT_WEIGHT` is set
  > (see the local patch in [VENDORED.md](./VENDORED.md)). With the default
  > weight of 0, `soft` is recorded and fed to reflection but never decides
  > accept/reject, so fixtures must keep baseline `hard` below 1.0 or no edit can
  > be accepted. To optimize *process* rather than success rate, set the weight.

```
trainer (vendored)
  rollout ─ claude_code_exec runs Claude Code in a prepared workspace (Read/Edit/Write/Bash)
          │  ├─ hard = fixture test red→green (evaluator runs it; agent can't fake it)
          │  └─ soft = per-skill rubric judge on the trajectory (verbatim-evidence → 0)
  reflect ─ generic analyst proposes skill edits from failed/succeeded minibatches
  gate    ─ accept the edit only if mean reward improves on the val split
```

## Run it

Prereqs: the `claude` CLI on PATH and authenticated; Python deps from
[requirements.txt](./requirements.txt) (`pyyaml numpy openai httpx pytest`).
Each rollout is a multi-turn agentic Claude Code run that spends **real Claude
tokens**, so keep the pilot small.

```bash
cd distillery/skillopt

# (re)generate the fixture task set; each task is red on its bug, green when fixed
python fixtures/debugging/build_fixtures.py

# optimize ia-debugging; outputs land under outputs/ (gitignored)
PYTHONPATH=. python scripts/train.py --config configs/whetstone/default.yaml

# smaller/cheaper smoke run
PYTHONPATH=. python scripts/train.py --config configs/whetstone/default.yaml \
    --num_epochs 1 --batch_size 4
```

Output (under the run's `out_root`): `best_skill.md` (best validated skill),
per-step skill snapshots, `history.json`, and `predictions/<task-id>/` rollout
artifacts. **Promotion to the plugin stays manual and gated by the existing
`test-triggers` regression.** The optimizer changes skill content, not skill
activation.

## Layout

```
distillery/skillopt/
  skillopt/                     # vendored SkillOpt (trimmed); see VENDORED.md
    engine/ model/ gradient/ optimizer/ evaluation/ datasets/ prompts/ ...
    envs/base.py  envs/_template/   # the env interface + reference template
    envs/whetstone/             # ours: the only registered env
      adapter.py                #   EnvAdapter: wires dataloader + rollout + reflect
      dataloader.py             #   fixture tasks → train/val/test
      rollout.py                #   agentic claude_code_exec rollout + scoring
      evaluator.py              #   hybrid reward: hard (pytest) + soft (rubric)
      rubric.py                 #   per-skill process rubric + verbatim-evidence judge
      skills/initial.md         #   seed = a copy of the shipped ia-debugging SKILL.md
  configs/whetstone/            # ours: default.yaml plus one config per onboarded skill
  fixtures/<skill>/             # ours: seeded tasks + splits + builder per fixture set
  scripts/train.py              # vendored entry (registry trimmed to whetstone)
```

## Adding a skill

1. Add a rubric for it to `skillopt/envs/whetstone/rubric.py` (criteria mirror the
   skill's own rules; weights sum to 1.0). Keep it in sync when the SKILL.md changes.
2. Decide the deterministic `hard` for that skill (debugging: tests pass; planning:
   a `.plan/` with required sections; verification: the verify command appears as an
   executed tool call). Extend `evaluator.py` accordingly.
3. Build a task set under `fixtures/<skill>/` and point a new config at it.

## How this differs from `evolve`

`distiller.py evolve` uses DSPy GEPA/MIPROv2 and scores **single-turn** generations
(`dspy.ChainOfThought`) against a keyword/LLM-judge fitness. This optimizer runs the
skill **agentically** (real tools, multi-turn) and gates on a **deterministic
outcome** plus a process rubric. `evolve` is cheap and fast for prompt-shaped
tuning; `skillopt` is the higher-fidelity, higher-cost path for process skills
whose value only shows up in agentic execution.

## Caveats

- **Cost.** One rollout per item per gate check; each is an agentic Claude Code run.
  Pilot stays at single-digit batch/epoch.
- **Sandbox.** Rollouts run an autonomous `bypassPermissions` Claude Code agent and
  execute its edited code (pytest) in a disposable out-of-repo tmpdir. Point it
  only at trusted, curated fixtures, never an untrusted task set. See the Safety
  section of [SKILLOPT-RUNBOOK.md](./SKILLOPT-RUNBOOK.md).
- **`soft` is an LLM judge.** Verbatim-evidence grounding (ungrounded quote → 0.0)
  and harness-verified artifacts block the obvious reward-hacking paths, but editor
  and judge share a model family and the temporal criteria are still
  report-derived. Inspect accepted edits in `history.json`.
- **Vendoring drift.** Pinned in VENDORED.md; re-vendor deliberately.
