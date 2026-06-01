# SkillOpt Runbook — optimizing a process skill

How to use `distillery/skillopt/` to improve a Whetstone **process** skill, end to
end. This is the repeatable procedure behind the pilot; for what the package *is*,
see [README.md](./README.md) and [VENDORED.md](./VENDORED.md).

SkillOpt is the **Tier 3** rung of the skill-optimization ladder — expensive,
triggered, offline. It is not in the release pipeline and not automatic.

| Tier | Tool | Cost | Use for |
|---|---|---|---|
| 1 | `distiller.py dspy-eval` / `eval-skills` | cheap | rank skills, find weak ones |
| 2 | `distiller.py evolve` (DSPy) | cheap | single-turn prompt tuning |
| 3 | **SkillOpt** | expensive | a **process** skill whose value is agentic, where Tier 2 plateaued |

## 1. When to reach for it (trigger)

All of these should hold:

- `eval-skills` / `diagnose-negatives` shows a **recurring process failure** in a
  `discipline`/`workflow` skill (debugging, verification-before-completion,
  code-review, writing-tests, planning, simplifying-code).
- `evolve` (cheap, single-turn) did not move the score.
- The skill's value shows up **agentically** (multi-turn, real tools).
- You can express the process as a fixture set + a rubric + a deterministic `hard`.

Skip for `language`/`reference` skills (no deterministic outcome) and anything
`evolve` already fixed.

## 2. The recipe (validated 2026-05-31)

1. **Target the model that has the gap, not the strongest one.** Capable models
   (Sonnet) *saturate* `hard` on tractable bugs — they fix everything and already
   follow the process (soft ≈ 0.78), so there is no room to improve. Optimize for
   the **weaker model that actually runs the skill** (e.g. `claude-haiku-4-5`
   subagents): it fixes the bugs but skips the process (soft ≈ 0.17), so the
   guidance has leverage. Keep the optimizer/judge on Sonnet (`claude_chat`).
2. **Blend `soft` into the gate.** Set `SKILLOPT_SOFT_WEIGHT` with
   **`λ < 1 / n_val`**. For a process skill this is *required*: the vendored gate
   selects on `hard` only, which saturates, so a hard-only gate can never accept a
   process improvement. The `λ < 1/n` bound preserves the deterministic floor — a
   lost fix costs `1/n` of `hard`, which no `soft` gain can buy back. (Validated:
   `λ=0.15`, `n=5` accepted a process-improving edit and rejected a `hard`-
   regressing one.)
3. **Get a discriminating signal.** Either a weak target with soft headroom (cheap,
   what worked) or genuinely hard multi-file/concurrency bugs that drop baseline
   `hard` below 1.0 (expensive to author). Prefer the weak target.

## 3. Safety — non-negotiable

The rollout drives an autonomous `bypassPermissions` agent with its bash sandbox
disabled (`CLAUDE_CODE_SANDBOXED=1`, needed to dodge the bubblewrap empty-overlay).
Claude Code's Bash tool runs at the nearest `.git` ancestor. During the pilot a
target agent ran repo-relative `rm -rf` and `git commit` and modified the host repo.

- **Run from a bare terminal — never nested inside a Claude Code session.** A nested
  child inherits the parent session's project root (`CLAUDE_CODE_COORDINATOR_MODE`),
  so even an out-of-repo workspace resolves back to the parent repo.
- **`git`-checkpoint before each run; keep fixtures tracked** so damage is
  `git`-recoverable.
- The rollout already isolates each `work_dir` in an out-of-repo tmpdir (closes
  relative-path escape). **Absolute-path access is still open** — for anything
  beyond your own curated fixtures, add OS-level sandboxing (container, firejail,
  restricted user). `bypassPermissions` + `CLAUDE_CODE_SANDBOXED=1` is the opposite
  of a sandbox.

## 4. Run it

```bash
cd distillery/skillopt

# 1. (re)build + verify the fixtures: each must be RED on the bug, GREEN on the fix
python fixtures/<skill>/build_fixtures.py
python fixtures/<skill>/build_fixtures.py --verify

# 2. optimize — weak target + soft-weighted gate (set lambda < 1/n_val)
SKILLOPT_SOFT_WEIGHT=0.15 PYTHONPATH=. python scripts/train.py \
    --config configs/whetstone/default.yaml \
    --cfg-options env.split_dir=fixtures/<skill>/splits env.tasks_root=fixtures/<skill>/tasks \
    --target_model claude-haiku-4-5 \
    --num_epochs 2 --batch_size 5 --eval_test false
```

Output lands under `outputs/<run>/`: `best_skill.md`, `history.json`, per-step
`skills/` snapshots, and `predictions/<task-id>/` artifacts. Read `history.json`
for the per-step `selection_hard` / `action` (accept / reject) and diff
`best_skill.md` against the seed to see the winning edit.

## 5. Onboarding a new process skill

1. Add its rubric to `skillopt/envs/whetstone/rubric.py` — criteria mirror the
   skill's own rules; weights sum to 1.0. Keep it in sync when the SKILL.md changes.
2. Decide its deterministic `hard` in `evaluator.py` (debugging: test passes;
   verification: the verify command appears as an executed tool call; planning: a
   `.plan/` with the required sections).
3. Build a fixture set under `fixtures/<skill>/` (model on `fixtures/debugging-hard/`).
   Every fixture must be red-on-bug / green-on-fix — verify before any rollout.
4. Choose `SKILLOPT_SOFT_WEIGHT < 1 / n_val` for your validation split size.

## 6. Promotion — manual and gated

`best_skill.md` is a **proposal**, never auto-shipped:

1. Inspect `history.json` for reward-hacking; review the `best_skill.md` diff.
2. **Re-eval on held-out / golden data** (`distiller.py dspy-eval`) — the in-run
   `val` may overlap `train`, so confirm the gain generalizes out of sample.
3. `distiller.py test-triggers` — confirm activation is unchanged (content edit,
   not an activation edit).
4. Run a Codex Flow A cycle — it is a behavior-affecting edit to a shipped skill.
5. Commit the SKILL.md change; `/release` ships it later.

## 7. Cost

Every rollout is a multi-turn agentic Claude Code run. Keep batch/epoch single-digit.
Triggered, not routine. The validated pilot run: ~60k tokens, ~21 min, 2 steps.

## Proof of concept

ia-debugging, `claude-haiku-4-5` target, blended gate (`SKILLOPT_SOFT_WEIGHT=0.15`,
n=5). The optimizer **accepted** an edit that lifted haiku's `soft` 0.17 → 0.34
while keeping `hard` at 1.0, and **rejected** a later edit that regressed `hard`
(the floor held). The accepted edit added: *"When a test file already exists, run
it immediately as the very first action — before reading any source or forming
hypotheses,"* directly targeting haiku's observed skip-reproduction failure.
