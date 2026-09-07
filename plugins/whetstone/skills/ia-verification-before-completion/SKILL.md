---
name: ia-verification-before-completion
class: discipline
description: >-
  Enforces fresh verification evidence before any completion claim. Use when
  about to claim "tests pass", "bug fixed", "done", "ready to merge", handing
  off work, or before editing when a request has ambiguous scope.
---

# Verification before completion

Make completion claims only from fresh evidence for the actual claim. Follow the user's authorized scope; repository instructions supply applicable checks, not permission to mutate, publish, or weaken a requirement.

## Procedure

1. Resolve ambiguous scope before editing. Inspect the repository and state a safe assumption when one interpretation is clear. Ask only when materially different interpretations remain; do not edit the disputed scope while waiting.
2. Inspect `git status --porcelain` and preserve unrelated work. For dependency/framework upgrades, codegen, or migrations, capture the existing validation command set before writing and rerun it unchanged afterward. If that baseline is red, report before proceeding. Shared-module verification on a dirty tree needs an isolated base comparison.
3. **Identify** the command that proves the claim. For ship-level claims, check the full applicable chain: build, types, lint, tests, security scan, and diff review; stop on the first failure. Read project-declared gates and run the ones that apply to this action in their required order; do not invent gates.
4. **Run** the proof now. Earlier output, a subagent's report, confidence, and a renamed success phrase do not replace fresh execution.
5. **Read** complete output and exit status, including warnings, executed/passed counts, and missing artifacts. A suite that executes nothing is not proof. Confirm the intended binary, interpreter, source revision, and entry point actually ran.
6. **Verify** that evidence covers the requirements and relevant failure paths. An implemented safe positive capability must work through its intended entry point; a refusal-only path, stub, mock, or unreachable implementation is partial.
7. **Claim** only what the evidence establishes. Report the outcome, exercise command/URL/click path, failed or skipped checks, and material residual risks. State narrower proof scope and distinguish deterministic fixtures from live behavior.

Never make an oracle easier to satisfy to obtain green. Review and justify semantic changes before regenerating expected output. Never hard-code the exercised subject or success path. A clean review is valid when it covers the relevant criteria; broaden checks only for a named remaining risk.

## Route by verification risk

- For dirty worktrees, broad changes, strict input validation, or fixture-versus-live provenance, read [proof-integrity.md](./references/proof-integrity.md). For shared modules with unrelated edits, also read [isolated-verification.md](./references/isolated-verification.md).
- For repository-wide sweeps or “every item” claims, read [scope-and-sweeps.md](./references/scope-and-sweeps.md). Enumerate every item in untracked/ignored scratch state, preserve explicit dispositions, re-enumerate after moves, and account for removals. Completion requires zero pending and zero blocked items.
- For command wrappers, empty results, aggregate totals, installed binaries, or materialized revisions, read [verification-oracles.md](./references/verification-oracles.md). Require positive controls through the same invocation shape before interpreting an absence.
- For frontend, backend, CLI, infrastructure, migration, package, schema, documentation, or scripted-sweep changes, read the matching row of [change-strategies.md](./references/change-strategies.md). It also covers adversarial probes, history rewrites, and stale reviews.
- For integration boundaries, callbacks, or orphaned state, read [system-wide-test-check.md](./references/system-wide-test-check.md).
- When classifying deliverables, handling failed checks, discussing branch scope, or encountering a pre-commit failure, read [claims-and-failures.md](./references/claims-and-failures.md).

## Failure and handoff rules

Do not retry unchanged verification until it happens to pass. Fix authorized implementation failures and rerun; otherwise name the concrete blocker. “Pre-existing,” “environmental,” and “flaky” require evidence against the deliberately chosen base or independently established cause.

Do not bypass a pre-commit failure caused by this work. The documented exception requires a reproduced base-branch failure and prior visibility to the user; this skill supplies no new bypass authority.

Verify delegated work directly through the diff and relevant command. Check specification compliance separately from quality. Re-read requirements line by line: passing tests and meeting requirements are different claims. Refresh facts and coordinates when new commits or external state could invalidate a prior review. Keep reports decision-relevant, without empty status sections or fabricated certainty.
