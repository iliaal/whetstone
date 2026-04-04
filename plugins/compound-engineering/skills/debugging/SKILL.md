---
name: debugging
description: >-
  Systematic root-cause debugging with verification. Use when debugging,
  troubleshooting, or facing errors, stack traces, broken tests, flaky tests,
  or regressions. For validating bug reports before fixing, use
  bug-reproduction-validator agent.
---

# Debugging

## The Iron Law

Never propose a fix without first identifying the root cause. "Quick fix now, investigate later" is forbidden -- it creates harder bugs. This applies ESPECIALLY under time pressure, when "just one quick fix" seems obvious, or when multiple fixes have already failed. Those are the moments this process matters most.

**Trivially obvious bugs** are their own root cause -- state the cause and fix directly. A bug is trivially obvious only when the **cause** is in the error message (e.g., `ModuleNotFoundError: no module named foo`, a typo in a string literal). If the error shows **where** something fails but not **why** (e.g., `TypeError: Cannot read 'id' of undefined`), it is not trivially obvious -- investigate why the value is undefined.

## Root Cause Analysis

Root cause identification is the core deliverable of debugging -- not the fix itself.

- **Trace backward**: Start at the symptom, walk the call chain in reverse to find where behavior diverges from expectation
- **Differential analysis**: Compare working vs broken state across dimensions (code version, data, environment, timing, configuration)
- **Regression hunting**: Use `git bisect` to pinpoint the exact commit that introduced the issue
- **Evidence-based**: Document root cause with `file:line` references, log output, and concrete reproduction proof. Root cause = the earliest point where behavior diverged from expectation, stated with evidence at least two levels deep (not just "it failed here" but "it failed here because X was null, and X was null because Y never set it")
- **Competing hypotheses**: When the cause is ambiguous, generate multiple hypotheses and rank by evidence strength (see Escalation section below)

## Environment Diagnostics

Capture environment state with `bash collect-diagnostics.sh` ([script](./scripts/collect-diagnostics.sh)). Use during differential analysis or attach to bug reports. See [specialized-patterns.md](./references/specialized-patterns.md) for details.

## Process

**0. Read the error.** Read the full error message, stack trace, and line numbers before doing anything. Error messages frequently contain the exact fix. Don't skim -- read the entire output.

**1. Reproduce** -- make the bug consistent. If intermittent, run N times under stress or simulate poor conditions (slow network, low memory) until it triggers reliably.

**1b. Form initial hypotheses** -- before investigating broadly, form 2-3 hypotheses based on the reproduction. What are the most likely causes given the symptoms? This focuses the investigation on plausible paths rather than searching aimlessly.

**1c. Reduce** -- strip the reproduction to the minimal failing case. Remove unrelated code, data, and configuration until removing one more piece makes the bug disappear. That remaining piece is the trigger.

**2. Investigate** -- trace backward through the call chain from the symptom. Compare working vs broken state using a differential table (environment, version, data, timing -- what changed?).

**Multi-component systems** (CI -> build -> deploy, API -> service -> DB): before proposing fixes, instrument each component boundary:
- Log what data **enters** the component
- Log what data **exits** the component
- Verify environment/config propagation across the boundary

Run once to gather evidence showing WHERE it breaks, then investigate that specific component. Use `console.error()` (not logger, which may be suppressed in tests). Log BEFORE the dangerous operation, not after it fails. Include context: cwd, env vars, `new Error().stack`.

**Pre-existing failure proof:** Before claiming a test failure is "not related to our changes," prove it. Run `git stash && [test command]` on clean state to confirm the failure exists on the base branch. Pre-existing without receipts is a lazy claim.

**Before external searches** (web, docs, forums): strip hostnames, IPs, file paths, SQL fragments, and customer data from the query. Raw stack traces leak privacy and return noise.

**3. Hypothesize and test** -- one change at a time. If a hypothesis is wrong, fully revert before testing the next. Use `git bisect` to find regressions efficiently. **Scope lock**: after forming a hypothesis, identify the narrowest affected directory or file set. Do not edit code outside that scope during the debug session. If the fix requires changes elsewhere, update the hypothesis first.

**4. Fix and verify** -- create a failing test FIRST, then fix. Run the test. Confirm the original reproduction case passes. No completion claims without fresh verification evidence (see `verification-before-completion`).

## Debug Report

Emit after every resolved bug. For non-trivial production bugs, also write a full Postmortem (see below).

After resolving, output a structured report:

```
SYMPTOM:    [What was observed]
ROOT CAUSE: [Why it happened -- file:line with evidence]
FIX:        [What changed]
EVIDENCE:   [Verification output proving the fix]
REGRESSION: [Test added to prevent recurrence]
```

## Three-Fix Threshold

After 3 failed fix attempts, STOP. An attempt = one complete hypothesis-test cycle (form hypothesis, make minimal change, verify). The problem is likely architectural, not a surface bug. Escalate to the user before attempting further fixes. Step back and question assumptions about how the system works. Read the actual code path end-to-end instead of spot-checking.

**Architectural problem indicators** -- signals the bug is structural, not a surface fix:
- Each fix reveals new shared state or coupling you didn't expect
- Fixes require massive refactoring to implement correctly
- Each fix creates new symptoms elsewhere in the system

**No root cause found:** If investigation is exhausted without a clear root cause, say so explicitly. Document what was checked, what was ruled out, and what instrumentation to add for next occurrence. An honest "unknown" with good diagnostics beats a fabricated cause.

## Escalation: Competing Hypotheses

When the cause is unclear across multiple components, use Analysis of Competing Hypotheses (ACH). Generate hypotheses across failure categories, collect evidence FOR and AGAINST each, rank by confidence, and investigate the strongest first.

See [competing-hypotheses.md](./references/competing-hypotheses.md) for the full methodology: six failure categories, evidence strength scale, confidence scoring, and anti-patterns.

## Intermittent Issues

For race conditions, deadlocks, resource exhaustion, and timing-dependent bugs, see [specialized-patterns.md](./references/specialized-patterns.md). Key signals: shared mutable state, check-then-act, circular lock acquisition, connection pool exhaustion under load.

## Defense-in-Depth Validation

After fixing, validate at every layer -- not just where the bug appeared. See [defense-in-depth.md](./references/defense-in-depth.md) for the four-layer pattern (entry, business logic, environment, instrumentation) with examples.

## Bug Triage

When multiple bugs exist, prioritize by:
- **Severity** (data loss > crash > wrong output > cosmetic) separately from **Priority** (blocking release > customer-facing > internal)
- Reproducibility: always > sometimes > once. "Sometimes" bugs need instrumentation before fixing.
- Quick wins: if a fix is < 5 minutes and unblocks others, do it first

## Common Patterns

- **Async ordering** -- missing `await`, unhandled promise rejection, callback firing before setup completes. The temporal gap between setup and callback is where bugs hide.
- **Stale state** -- cached values, stale closures, outdated config, old build artifacts. When behavior contradicts the code you're reading, verify you're running what you think you're running.
- **Recurring fix site** -- if `git log` shows 3+ prior fixes in the same file, the file needs redesign, not another patch. Escalate as architectural smell.

## Root Cause Tracing

When a bug manifests deep in the call stack, resist fixing where the error appears. Trace backward through the call chain to find the original trigger, then fix at the source. See [root-cause-tracing.md](./references/root-cause-tracing.md) for the full technique with stack instrumentation patterns and test pollution detection.

## Pattern Comparison

When the cause isn't obvious, find working similar code in the codebase and compare it structurally with the broken path. Read the working reference implementation completely -- don't skim. List every difference between working and broken, however small. Don't assume any difference can't matter. The bug is in one of them.

## Anti-Patterns and Red Flags

When you catch yourself doing or thinking these things, **stop and return to Step 1 (Reproduce)**:

| What You're Doing / Thinking | What It Really Means |
|-----------------------------|---------------------|
| Shotgun debugging -- random changes without a hypothesis | You're guessing. Form a hypothesis first, then revert and test one change. |
| Multiple simultaneous changes | You're making the problem harder to diagnose. One change at a time. |
| Fixing the symptom, not the cause | The same bug will resurface differently. Trace to root cause. |
| Ignoring intermittent failures ("works on my machine") | Instrument and reproduce under load instead. |
| "Skip the test, I can see it works" | You can't. Run the verification. See `verification-before-completion`. |
| "It's probably X" | "Probably" means you haven't verified. Trace the actual execution path. |
| "I see the problem, let me fix it" | Seeing symptoms is not understanding root cause. Trace the actual execution path first. |
| "Reference too long, I'll adapt the pattern" | Partial understanding guarantees bugs. Read the working example completely and apply it exactly. |
| "I'll clean up the debugging later" | Remove diagnostic code now or it ships to production. |
| "This failure is pre-existing, not related to our changes" | Prove it: run the test suite on the base branch. No receipts = no claim. |
| "The test is wrong, not the code" | Verify before dismissing. Read the test's intent. If the test is genuinely wrong, fix the test with a clear rationale, not a silent update. |
| "It works in isolation, must be an environment issue" | Isolation success doesn't explain integration failure. Instrument the integration boundary. |

See [specialized-patterns.md](./references/specialized-patterns.md) for anti-pattern signals and specialized debugging patterns.

## Verify

- Root cause identified with `file:line` evidence (not just "it failed here")
- Regression test exists and fails without the fix, passes with it
- Debug Report emitted with all five fields
- No diagnostic instrumentation left in code (`git diff` shows no leftover logging)

## Integration

This skill is referenced by:
- `workflows:work` -- during task execution for bug investigation
- `writing-tests` -- creating failing tests to reproduce bugs
- `verification-before-completion` -- before claiming a bug is fixed
- `bug-reproduction-validator` agent -- follows Root Cause Analysis methodology
- `devops-engineer` agent -- follows Postmortem template for production incidents
- `reproduce-bug` command -- automated bug reproduction workflow

## Postmortem

For non-trivial production bugs, write a lightweight postmortem (timeline, root cause, impact, fix, prevention). See [specialized-patterns.md](./references/specialized-patterns.md) for the template.
