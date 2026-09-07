---
name: ia-debugging
class: discipline
description: >-
  Systematic root-cause debugging with verification. Use for errors, stack
  traces, broken tests, flaky tests, regressions, or anything not working as
  expected. For validating bug reports before fixing, use
  bug-reproduction-validator agent.
---

# Debugging

Ground permanent repairs in an evidence-backed causal explanation. A hypothesis may justify a bounded reversible experiment; label it as experimental until verified. During an active incident, an authorized rollback or feature disable may restore service before root cause is known. Record remaining uncertainty and keep the repair investigation open: mitigation is not proof of repair.

## Scope and modes

For diagnosis-only requests, inspect source/artifacts and run safe read-only checks within caller authority; do not repair or violate a no-build constraint. Diagnosis may finish with an evidenced cause while its proposed repair remains unverified. Use `NEEDS_CONTEXT` only for information blocking the requested work.

Keep edits within the hypothesis's narrow file scope; revise the hypothesis before expanding it. Preserve other work. Before sharing diagnostics or searching externally, remove credentials, customer data, hostnames, IPs, paths, and SQL fragments as appropriate; use environment-sourced credentials rather than embedding secrets. Read [baseline-and-data-handling.md](./references/baseline-and-data-handling.md) for branch/build comparisons or diagnostic data sharing.

## Process

1. **Read and reproduce.** Read the full error and totals, not just filtered matches. Confirm HEAD after session resumption before trusting carried file content. Run a provided reproducer before editing. Match the reported symptom exactly; a nearby failure is not the same reproduction. Use the cheapest actual trigger. For intermittent bugs, bound attempts and report conditions/frequency; a finite clean run does not disprove a race. Read [reproduction-and-investigation.md](./references/reproduction-and-investigation.md) when constructing, reducing, or instrumenting a reproducer.
2. **Ground hypotheses.** Form two to three candidates, each citing an observation. A trivial verified typo needs only a short causal check; an import error alone does not identify why import failed. Reduce irrelevant inputs while retaining the actual trigger. If no loop is available, report missing access, artifacts, credentials, or steps, and continue independent source investigation without claiming reproduction.
3. **Trace and discriminate.** Explain the violated invariant and triggering conditions, without imposing a fixed stack depth. Compare code, inputs, state, timing, environment, and build configuration. Identical source that passes another build can still contain undefined behavior or races. Use [root-cause-tracing.md](./references/root-cause-tracing.md) for backward tracing/test pollution and [collect-diagnostics.sh](./scripts/collect-diagnostics.sh) for relevant environment captures. State the question and decision rule before probing; verify controls and build identity before trusting a result.
4. **Test one change.** Test a named causal hypothesis with a minimal experiment. Revert a disproved experiment before the next; use bisect for an introduced regression when appropriate. A failed remedy can mean an incomplete fix or wrong build rather than a disproved cause. Reassess the actual evidence before another experiment. For competing multi-component explanations, read [competing-hypotheses.md](./references/competing-hypotheses.md).
5. **Repair and verify.** For authorized fixes, read [repair-and-escalation.md](./references/repair-and-escalation.md). Create a regression that exercises the real trigger: red without the fix, green with it. If no reachable test seam exists, report it instead of substituting a test that cannot fail for the reported defect. Verify the original entry point with fresh evidence under `ia-verification-before-completion`; do not weaken assertions, swallow failures, or special-case the exercised input. Run a bypass self-check with a nearby input reaching the same bad state; return to root cause if it bypasses the change. Security-relevant fixes need a fresh adversarial re-attack under [specialized-patterns.md](./references/specialized-patterns.md). Trim the verified fix and remove diagnostic instrumentation.
6. **Reassess after three failed cycles.** Stop editing, reread the path, list failed assumptions, and escalate evidence. Three cycles are a retry budget, not proof of architectural failure. In diagnosis-only mode, three cycles without narrowing the component call for interim findings and the next instrumentation step. State an unknown cause honestly. Ask material missing questions through AskUserQuestion in Claude Code, request_user_input in Codex where supported, otherwise chat; unattended subagents return blockers to their parent.

For CI failures, rendering/async first moves, performance, intermittent failures, postmortems, or recurring patterns, read [specialized-patterns.md](./references/specialized-patterns.md). For a multi-layer validation defect, read [defense-in-depth.md](./references/defense-in-depth.md). Follow the detailed repair reference when diagnostic anti-patterns or repeated failed fixes appear.

## Debug report and completion

Emit the seven fields for the requested scope:

```text
SYMPTOM:    Observed failure
ROOT CAUSE: Evidenced causal conclusion with file:line, or remaining uncertainty
FIX:        Verified repair; use PROPOSED FIX and validation command in diagnosis-only mode
EVIDENCE:   Causal evidence and, for repairs, actual verification results
REGRESSION: Actual regression, or proposed test/missing seam when no repair was performed
RELATED:    Relevant prior bugs, risks, and architectural observations
STATUS:     DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
```

`DONE` means the repair was verified or the requested diagnosis was completed with evidence; it never certifies an untested proposed remedy. `DONE_WITH_CONCERNS` states completed scope and residual uncertainty. `BLOCKED` names the blocker; `NEEDS_CONTEXT` names required missing information. Mitigation alone does not close a repair request.

Before completing a repair, check causal evidence, actual regression coverage or its stated limit, bypass/re-attack results, and removal of diagnostic logging. For non-trivial production bugs, capture a lightweight timeline, cause, impact, fix, and prevention postmortem using the specialized reference.
