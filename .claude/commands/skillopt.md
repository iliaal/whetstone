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
- `--fixtures <dir>` (default `debugging-hard` for ia-debugging) — fixture set
  under `distillery/skillopt/fixtures/<dir>/`.
- `--target <model>` (default `claude-haiku-4-5`) — the **weak** target to optimize
  for; capable models saturate `hard`, leaving no room.
- `--weight <λ>` (default auto) — soft blend weight; must be `< 1/n_val`.
- `--epochs N` (default `2`).
- `--run` — execute in-session (hardened) instead of printing the command.

## Procedure (follow exactly)

1. **Resolve the fixture dir.** `FIXDIR = distillery/skillopt/fixtures/<--fixtures
   or default>`. Confirm `FIXDIR/build_fixtures.py`, `FIXDIR/splits/{train,val,test}/items.json`,
   and `FIXDIR/tasks/` exist. If not, tell the user to build/author the fixtures
   (see the runbook §5) and STOP.

2. **Validate fixtures** (deterministic, no tokens):
   `cd distillery/skillopt && python3 fixtures/<dir>/build_fixtures.py --verify`.
   Every line must read `[OK] … buggy=RED fixed=GREEN`. If any is `BROKEN`, STOP
   and report — a malformed fixture corrupts the run.

3. **Compute the soft weight.** Read `n = len(splits/val/items.json)`. The
   constraint is `λ < 1/n` (so soft can refine among correct fixes but never
   offset a lost fix). If `--weight` was given, verify `λ < 1/n` (else lower it and
   warn). Otherwise default `λ = min(0.15, round(0.8/n, 3))`. Report `n`, `1/n`,
   and the chosen `λ`.

4. **Verify the target CLI** is present: `claude --version` (the rollout shells
   `claude -p --model <target>`). If missing, STOP.

5. **Build the command** (fill in the resolved values; `--batch_size` = `n_train`):
   ```bash
   cd distillery/skillopt && SKILLOPT_SOFT_WEIGHT=<λ> PYTHONPATH=. python scripts/train.py \
     --config configs/whetstone/default.yaml \
     --cfg-options env.split_dir=fixtures/<dir>/splits env.tasks_root=fixtures/<dir>/tasks \
     --target_model <target> --num_epochs <N> --batch_size <n_train> --eval_test false
   ```

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
