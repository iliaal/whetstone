---
name: ia-python-services
class: language
description: >-
  Python patterns for CLI tools, async concurrency, and backend services. Use
  when working with Python code, building CLI apps, FastAPI services,
  async with asyncio, background jobs, or configuring uv, ruff, ty, pytest, or
  pyproject.toml.
paths:
  - "**/*.py"
  - "**/pyproject.toml"
  - "**/ruff.toml"
  - "**/uv.lock"
---

# Python Services & CLI

## Working rules

- Validate external inputs and responses at boundaries; preserve exception causes.
- **Keep missing results distinct from empty results.** When an empty collection means success, require the response field instead of defaulting it to empty; an all-default model can validate `{}` as success. Test missing, misspelled, explicitly empty, and populated payloads through the real validation boundary.
- Keep simple sequential work synchronous. Bound concurrent work, preserve cancellation, and keep task references.
- Give network calls timeouts; retry only failures and operations whose semantics permit it.
- Enforce job idempotency with atomic writes and database constraints.
- Preserve published API behavior and shared migration history.
- Match telemetry to an operational question and verify its output.

## Discipline

- Simplicity first: every change as simple as possible, impact minimal code
- Only touch what's necessary; avoid introducing unrelated changes
- No hacky workarounds: if a fix feels wrong, step back and implement the clean solution
- Before adding a new abstraction, verify it appears in 3+ places. If not, inline it.
- Verify with the project's configured checks and thresholds.


## Verify

Run the project's configured test, lint, and type-check commands. Use its coverage and warning thresholds. Report applicable checks that cannot run.

For new projects adopting these tools, starter checks are `uv run pytest`, `uv run ruff check .`, and `uv run ty check .`. With `pytest-cov` configured, `uv run pytest --cov` measures coverage. Use 80% as a starter target when the project establishes one. Add `--cov-report=html` for a browsable report.

## Task-specific references

Read the relevant reference before implementing or reviewing the matching behavior:

- For packaging, environment configuration, CLI setup, or pytest behavior: [tooling-and-tests.md](./references/tooling-and-tests.md).
- For asyncio, background jobs, retries, pooling, timeouts, or health checks: [concurrency-and-resilience.md](./references/concurrency-and-resilience.md).
- For APIs, validation, errors, migrations, logging, metrics, or traces: [service-boundaries.md](./references/service-boundaries.md).

Existing specialized references, when the corresponding topic applies:

- [cli-tools.md](./references/cli-tools.md).
- [fastapi.md](./references/fastapi.md).
