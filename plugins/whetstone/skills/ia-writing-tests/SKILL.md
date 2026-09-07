---
name: ia-writing-tests
class: discipline
description: >-
  Generic test writing discipline: test quality, real assertions, anti-patterns,
  and rationalization resistance. Use when writing tests, adding test coverage,
  or fixing failing tests for any language or framework. Complements
  language-specific skills.
---

# Writing tests

Produce tests that prove the requested behavior and fail when that behavior breaks. Follow user scope and the repository's actual contracts; this skill does not authorize implementation, external actions, or changes to acceptance criteria.

## Procedure

1. Discover the repository's runner, pinned wrapper, configuration, neighboring tests, and CI command before writing tests. Learn both focused and full-suite commands. Use project tooling rather than a global default; keep tracked scripts portable and apply personal wrappers only to the outer invocation.
2. Derive cases from user requirements, implemented behavior, and claims intended for the handoff. Map each acceptance criterion to a discriminating case that a plausible wrong implementation fails. Name tests by observable behavior; keep one behavior per test and make fixtures adversarial on the axis under test.
3. For bug fixes, write the reproducer, observe the intended failure, apply the smallest fix, and observe green. For new features, develop tests alongside the implementation. Refactor after green. Never alter a specification, assertion, fixture, snapshot, or expected output merely to make the implementation pass.
4. Prefer real internal objects, real temporary files, and real test databases. Mock only external boundaries, at the last owned adapter; framework-maintained fakes are appropriate where the framework recommends them. Check the real contract and side effects before mocking.
5. Assert consumer-visible outcomes rather than private structure, mock calls, or framework behavior. Include relevant boundary, invalid-input, concurrency, and failure cases. If error handling catches, logs, substitutes, or rolls back, assert its observable result as well as error visibility.
6. Prove absence/isolation assertions with a run-unique forbidden violation and observe that specific assertion fail. Confirm the control mutation actually landed and its build completed before evaluating it. Remove the control, restore the artifact, and verify green.
7. Run the narrow checks during edits and the applicable complete checks before handoff. Inspect passed/executed counts; an empty or skipped suite is not positive evidence. Report failures and skipped checks accurately.

## Select the detail needed

- When choosing cases, fixture shape, mock boundaries, or unit/integration/E2E balance, read [test-design.md](./references/test-design.md).
- For bug reproducers, mutation controls, or assertions that something must not happen, read [regression-proof.md](./references/regression-proof.md).
- When reviewing generated tests, changing snapshots, testing async timing, or seeing mocks substitute for behavior, read [test-smells.md](./references/test-smells.md) and the applicable fix ladder in [anti-patterns-extended.md](./references/anti-patterns-extended.md).
- For weak aggregates, vacuous assertions, race reproduction, or controls that may never reach their subject, read [oracle-smells.md](./references/oracle-smells.md). It routes to the longer catalogs when those failure shapes apply.
- For container state, sandboxing, timeouts, environment relocation, or process/stream isolation, read [isolation-and-sandbox-traps.md](./references/isolation-and-sandbox-traps.md).
- For wrappers, filters, conformance oracles, skip conditions, or misleading green summaries, read [false-pass-oracle-traps.md](./references/false-pass-oracle-traps.md).
- When byte equivalence or a generated corpus is the contract, read [generated-corpus-techniques.md](./references/generated-corpus-techniques.md); compare against an independent implementation across value shapes and nesting.
- When stuck, considering skipping tests, or assembling a test-work handoff, read [test-completion.md](./references/test-completion.md). Before arguing against a needed test, read [rationalization-table.md](./references/rationalization-table.md).

## Verify and report

Verify public behavior and edge paths, independence between tests, reviewed expectation changes, and each claimed capability. Bug tests must fail on the unfixed code. Mentally remove a guard, flip a branch, or drop a side effect and confirm a test detects it. Prefer a unit suite fast enough for frequent use (under 30 seconds).

Report what the tests exercised, actual results, failures, and omissions. Distinguish fixtures from live proof. Use the applicable PHP/Laravel or React/TypeScript skill for framework conventions; this generic skill does not replace them.
