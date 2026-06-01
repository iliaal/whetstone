---
name: skillopt
description: "Run the SkillOpt process-skill optimizer (offline, local). Default prints the exact bare-terminal command (safe); --run executes it in-session (hardened + checkpointed)."
argument-hint: "[skill=ia-debugging] [--fixtures <dir>] [--target <model>] [--weight <λ>] [--epochs N] [--run]"
---

# /skillopt — run the SkillOpt process-skill optimizer

Optimize a Whetstone **process** skill via `distillery/skillopt/`. Full procedure
and rationale: `distillery/skillopt/SKILLOPT-RUNBOOK.md`.

## Safety — read before `--run`

The optimizer drives a `bypassPermissions` target agent with its bash sandbox
disabled. Running it **nested inside a Claude Code session** is the documented
hazard that has let a target agent `rm -rf` fixtures and `git commit` in the host
repo (see the Safety section of `distillery/skillopt/SKILLOPT-RUNBOOK.md`).
Therefore:

- **Default mode does NOT run the agent in-session** — it validates + prints the
  exact command to run in a bare terminal.
- `--run` executes in-session only after the rollout's `_ensure_unsandboxed`
  unsets `CLAUDE_CODE_COORDINATOR_MODE` (confines each nested agent's Bash root to
  its out-of-repo tmpdir) AND a clean git checkpoint exists. Relative-path escape
  is closed by design; **absolute-path access still is not** — use `--run` only on
  your own curated fixtures, and prefer the default.

## Arguments

- `skill` (default `ia-debugging`) — the process skill to optimize.
- `--fixtures <dir>` (advanced) — override the fixture set named in the skill's
  config; defaults to whatever `configs/whetstone/<skill>.yaml` points at.
- `--target <model>` (default: the config's weak target) — override the **weak**
  target to optimize for; capable models saturate `hard`, leaving no room.
- `--weight <λ>` (default auto) — soft blend weight; must be `< 1/n_val`.
- `--epochs N` (default `2`).
- `--run` — execute in-session (hardened) instead of printing the command.

## Procedure (follow exactly)

1. **Resolve the per-skill config.** `CONFIG = distillery/skillopt/configs/whetstone/<skill>.yaml`.
   If it does not exist, the skill is **not onboarded** — SkillOpt needs four pieces
   per skill: fixtures, a `RUBRICS[<skill>]` entry in
   `skillopt/envs/whetstone/rubric.py`, this config, and a seed (`env.skill_init`).
   Tell the user to onboard it (see the runbook §5) and STOP. **Do not fall back to
   `default.yaml`** — that silently optimizes ia-debugging's skill against the wrong
   fixtures. Read `FIXDIR` from the config's `env.tasks_root`; confirm `FIXDIR`, the
   sibling `splits/{train,val,test}/items.json`, and the set's `build_fixtures.py`
   exist.

2. **Validate fixtures** (deterministic, no tokens):
   `cd distillery/skillopt && python3 <FIXDIR>/build_fixtures.py --verify`. Every
   line must be `[OK] …` (red-on-seed / green-on-fix — the exact wording varies per
   set, e.g. `buggy=RED fixed=GREEN` or `cluttered=RED simplified=GREEN`). If any is
   `BROKEN`, STOP and report — a malformed fixture corrupts the run.

3. **Compute the soft weight.** Read `n = len(splits/val/items.json)`. The
   constraint is `λ < 1/n` (so soft can refine among correct fixes but never
   offset a lost fix). If `--weight` was given, verify `λ < 1/n` (else lower it and
   warn). Otherwise default `λ = min(0.15, round(0.8/n, 3))`. Report `n`, `1/n`,
   and the chosen `λ`.

4. **Verify the target CLI** is present: `claude --version` (the rollout shells
   `claude -p --model <target>`). If missing, STOP.

5. **Build the command** (the per-skill `CONFIG` already owns `skill_name`,
   `skill_init`, the fixture paths, and the weak `target`; `--batch_size` = `n_train`):
   ```bash
   cd distillery/skillopt && SKILLOPT_SOFT_WEIGHT=<λ> PYTHONPATH=. python scripts/train.py \
     --config configs/whetstone/<skill>.yaml \
     --num_epochs <N> --batch_size <n_train> --eval_test false
   ```
   Add `--target_model <target>` only to override the config's weak target, or
   `--cfg-options env.tasks_root=fixtures/<dir>/tasks env.split_dir=fixtures/<dir>/splits`
   only when `--fixtures` overrode the set.

6. **Default (no `--run`)** — print the command above in a copy-paste block,
   preceded by: "Run this in a **bare terminal** (a separate shell, not inside
   Claude Code). Outputs land under `distillery/skillopt/outputs/<run>/`." Then
   STOP. Do not execute it.

7. **`--run`** — only if `git status --porcelain` (repo root) is **empty**
   (a clean checkpoint to recover to). If the tree is dirty, tell the user to
   commit/stash first and STOP. Record `git rev-parse --short HEAD` as the
   recovery point, then run the command with `run_in_background: true` and monitor
   the log for `baseline result`, `EVALUATE`, `ACCEPT`/`REJECT`, tracebacks, and
   `Output saved`.

8. **After completion** (either mode, once the user has a finished run dir):
   read `outputs/<run>/history.json` (per-step `selection_hard` + `action`), diff
   `best_skill.md` against the seed skill, and report what changed and whether the
   gate accepted. Remind: **promotion is manual + gated** — inspect for
   reward-hacking, re-eval on held-out/golden data (`distiller.py dspy-eval`),
   `distiller.py test-triggers`, Codex Flow A cycle, then commit; `/release` ships
   it. Never auto-promote `best_skill.md`.
