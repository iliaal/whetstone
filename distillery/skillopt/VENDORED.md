# Vendored: microsoft/SkillOpt

The `skillopt/` package, `scripts/train.py`, and `configs/_base_/` here are
**vendored** from microsoft/SkillOpt and lightly trimmed. They are not our code;
treat them as a pinned dependency. The whetstone-specific code lives in
`skillopt/envs/whetstone/`, `configs/whetstone/`, and `fixtures/`.

| | |
|---|---|
| Upstream | https://github.com/microsoft/SkillOpt |
| Commit | `75b5c7f31c040b4e8845877f1f2dd664bf366b11` |
| Vendored | 2026-05-29 |
| License | MIT (see `LICENSE`) |

## What was changed from upstream

- **Dropped benchmark envs** we don't use: `skillopt/envs/{alfworld, docvqa,
  livemathematicianbench, officeqa, searchqa, spreadsheetbench}` and their
  `configs/` + `data/`. Kept `envs/base.py`, `envs/__init__.py`, `envs/_template/`.
- **Trimmed `scripts/train.py`** `_register_builtins()` to register only the
  `whetstone` env (upstream registered ~12 benchmark adapters via try/except).
- **Patched `skillopt/model/codex_harness.py`** (`_run_claude_code_cli_exec`):
  dropped the `--tools <tools>` flag from the `claude -p` command. In the
  installed claude CLI (2.1.x) that flag breaks tool execution — the model
  degrades to emitting `<function_calls>` markup as plain text and never runs
  tools. `--allowedTools` alone gives the correct allow-list. The change is
  marked with a `LOCAL VENDOR PATCH` comment at the edit site.
- Everything else under `skillopt/` (engine, model, gradient, optimizer,
  evaluation, scheduler, datasets, prompts, utils, config.py, types.py) is
  **unmodified** upstream.

The whetstone rollout also sets `CLAUDE_CODE_SANDBOXED=1` for the target
subprocess (in `envs/whetstone/rollout.py`): Claude Code's bubblewrap Bash
sandbox otherwise overlays an empty view over the prepared workspace, so the
agent can't see the fixture. We isolate each rollout in a disposable work_dir
instead.

## Re-vendoring

Deliberate, never silent. To bump to a newer upstream:

1. `git clone https://github.com/microsoft/SkillOpt /tmp/SkillOpt && (cd /tmp/SkillOpt && git checkout <new-sha>)`
2. Re-copy `skillopt/` (minus the dropped envs), `scripts/train.py`, `configs/_base_/`, `LICENSE`.
3. Re-apply the `_register_builtins()` trim (whetstone-only).
4. Re-run the import smoke test and the pilot dry-run (see `README.md`).
5. Update the commit SHA + date in this file.

## Why vendored (not a pip dependency)

SkillOpt is not on PyPI, ships benchmark deps we don't need, and its env registry
lives in `scripts/train.py` (not plugin-friendly). Vendoring lets us trim, pin,
and keep `distillery/skillopt/` self-contained and reproducible.
