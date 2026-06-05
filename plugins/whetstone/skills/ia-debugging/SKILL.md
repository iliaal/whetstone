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

**1. Reproduce** -- build a feedback loop, *then* make the bug consistent. The loop is the deliverable of this step, not the analysis. Without a fast, deterministic signal that says "broken / fixed," every later step is guesswork.

**A loop already provided? Run it before touching source.** If the workspace already has a test file, or the report says "run X to see the failure," that command *is* your feedback loop: run it before reading source files or forming hypotheses (after reading the error in Step 0), and record the RED output. Do not edit source until you have observed a failing run this session; without RED first, you cannot prove your fix changed anything.

Pick the cheapest loop that triggers the bug:

- Failing test (preferred -- becomes the regression test in step 6)
- `curl` script or `httpie` invocation against a local server
- CLI harness or REPL session
- Headless browser script (Playwright, Puppeteer)
- Log replay against a captured request body
- Throwaway harness in `/tmp/` -- delete when done
- Property-based test (Hypothesis, fast-check)
- HITL bash session with manual reproduction steps documented

(`git bisect` and differential analysis are *strategies* applied during Step 5 and Pattern Comparison, not feedback loops -- they answer "which change broke it?" or "how does broken differ from working?" rather than "is it broken right now?")

If the bug is intermittent, run the loop N times under stress or simulate poor conditions (slow network, low memory) until it triggers reliably.

**Cannot build a loop?** Stop. State exactly what is missing -- access, credentials, artifacts, repro steps -- and ask the user. Do not proceed to investigate without a signal; you will pattern-match instead of debug.

**2. Form initial hypotheses** -- before investigating broadly, form 2-3 hypotheses based on the reproduction. What are the most likely causes given the symptoms? This focuses the investigation on plausible paths rather than searching aimlessly.

For each hypothesis, cite **at least one concrete observation** that supports it: a runtime variable value, a log line, an instrumented boundary capture, a behavior delta against a working comparison case, or a specific code reference. "X seems off" is not evidence; "X equals null at line 42 because Y was never initialized in the path that runs under condition Z" is. Hypotheses without grounding observations are theorizing -- go back and instrument until you have an observable signal (extend the Step 1 loop, or add Step 4 boundary captures).

**3. Reduce** -- strip the reproduction to the minimal failing case. Remove unrelated code, data, and configuration until removing one more piece makes the bug disappear. That remaining piece is the trigger.

**4. Investigate** -- trace backward through the call chain from the symptom. Compare working vs broken state using a differential table (environment, version, data, timing -- what changed?).

**Multi-component systems** (CI -> build -> deploy, API -> service -> DB): before proposing fixes, instrument each component boundary:
- Log what data **enters** the component
- Log what data **exits** the component
- Verify environment/config propagation across the boundary

Run once to gather evidence showing WHERE it breaks, then investigate that specific component. Use `console.error()` (not logger, which may be suppressed in tests). Log BEFORE the dangerous operation, not after it fails. Include context: cwd, env vars, `new Error().stack`.

**Pre-existing failure proof:** Before claiming a test failure is "not related to our changes," prove it. Run `git stash && [test command]` on clean state to confirm the failure exists on the base branch. Pre-existing without receipts is a lazy claim.

**Before external searches** (web, docs, forums): strip hostnames, IPs, file paths, SQL fragments, and customer data from the query. Raw stack traces leak privacy and return noise.

**5. Hypothesize and test** -- one change at a time. If a hypothesis is wrong, fully revert before testing the next. Use `git bisect` to find regressions efficiently. **Scope lock**: after forming a hypothesis, identify the narrowest affected directory or file set. Do not edit code outside that scope during the debug session. If the fix requires changes elsewhere, update the hypothesis first.

**6. Fix and verify** -- create a failing test FIRST, then fix. Run the test. Confirm the original reproduction case passes. No completion claims without fresh verification evidence (see `ia-verification-before-completion`).

**Reproduce-passes is not fixed.** Stopping the exact reproduction case is easy; the bad state is often still reachable from a nearby variant when the fix landed at the crash site, not the root cause. Before declaring done, run the **bypass self-check**: name one input variation that reaches the same bad state without tripping your change. If you can, the fix is at the wrong layer -- return to root cause. For security-relevant bugs, escalate to an **adversarial re-attack**: a fresh-context agent, blind to your fix reasoning, attacks the patched code to find a variant that still triggers it.

**Suppression is not a fix.** The bypass self-check assumes the fix attacks the bug -- confirm it actually does. A fix that swallows the error (`try/except: pass`, a blanket catch), disables the failing assertion, or special-cases the reproduction input makes the signal disappear while the defect lives on. A global swallow even *passes* the bypass check, because nothing reaches the bad state anymore. The fix must change behavior at the root cause, not hide the symptom.

**Trim to the minimal diff.** After the fix verifies, run a fresh-context pass asked only to "simplify to the smallest change that fixes the root cause." The fixing session is anchored to its own reasoning and over-reaches; a blind pass reliably finds the trim points without reintroducing the bug.

**On a failed fix:** return to Step 5 and *explicitly invalidate the current hypothesis* before forming a new one. State what evidence ruled out the prior hypothesis, then form a new hypothesis with its own grounding observation. Do not retry variants of the same theory ("maybe it was the other branch", "let me also catch this case") -- that is rationalization, not iteration. The Three-Fix Threshold below counts cycles, not retries within a single broken theory.

## Debug Report

Emit after every resolved bug. For non-trivial production bugs, also write a full Postmortem (see below).

After resolving, output a structured report:

```
SYMPTOM:    [What was observed]
ROOT CAUSE: [Why it happened -- file:line with evidence]
FIX:        [What changed]
EVIDENCE:   [Verification output proving the fix]
REGRESSION: [Test added to prevent recurrence]
RELATED:    [Prior bugs in same area, known issues, architectural notes]
STATUS:     DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT (definitions in `ia-verification-before-completion`)
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

## Common Patterns and Bug Triage

For the recurring-pattern catalog (async ordering, stale state, stale build artifacts, recurring fix site) and the severity-vs-priority triage heuristic when multiple bugs compete, see [specialized-patterns.md](./references/specialized-patterns.md).

## Root Cause Tracing

When a bug manifests deep in the call stack, resist fixing where the error appears. Trace backward through the call chain to find the original trigger, then fix at the source. See [root-cause-tracing.md](./references/root-cause-tracing.md) for the full technique with stack instrumentation patterns and test pollution detection.

## Pattern Comparison

When the cause isn't obvious, find working similar code in the codebase and compare it structurally with the broken path. Read the working reference implementation completely -- don't skim. List every difference between working and broken, however small. Don't assume any difference can't matter. The bug is in one of them.

## Anti-Patterns and Red Flags

When you catch yourself doing or thinking these things, **stop and return to Step 1 (Reproduce)**:

| What You're Doing / Thinking | What It Really Means |
|-----------------------------|---------------------|
| Shotgun debugging / "I see the problem, let me fix it" / "It's probably X" | Reasoning is not evidence. Form a hypothesis, make one change, test, revert if wrong. Trace the actual execution path. |
| Ignoring intermittent failures ("works on my machine") | Instrument and reproduce under load. Isolation success doesn't explain integration failure. |
| "I'll clean up the debugging later" | Remove diagnostic code now or it ships to production. |
| "This failure is pre-existing, not related to our changes" | Prove it: run the test suite on the base branch. No receipts = no claim. |
| "The test is wrong, not the code" | Verify before dismissing. Read the test's intent. If the test is genuinely wrong, fix it with a clear rationale, not a silent update. |
| "Reference too long, I'll adapt the pattern" | Partial understanding guarantees bugs. Read the working example completely and apply it exactly. |

See [specialized-patterns.md](./references/specialized-patterns.md) for anti-pattern signals and specialized debugging patterns.

## Verify

- Root cause identified with `file:line` evidence (not just "it failed here")
- Regression test exists and fails without the fix, passes with it
- Bypass self-check run: no variant input reaches the same bad state without tripping the fix (for security-relevant fixes, adversarial re-attack found no bypass)
- Debug Report emitted with all seven fields (SYMPTOM, ROOT CAUSE, FIX, EVIDENCE, REGRESSION, RELATED, STATUS)
- No diagnostic instrumentation left in code (`git diff` shows no leftover logging)

## Integration

This skill is referenced by:
- `/ia-work` -- during task execution for bug investigation
- `ia-writing-tests` -- creating failing tests to reproduce bugs
- `ia-verification-before-completion` -- before claiming a bug is fixed
- `ia-bug-reproduction-validator` agent -- follows Root Cause Analysis methodology
- `ia-infrastructure-engineer` agent -- follows Postmortem template for production incidents
- `ia-reproduce-bug` command -- automated bug reproduction workflow

## Postmortem

For non-trivial production bugs, write a lightweight postmortem (timeline, root cause, impact, fix, prevention). See [specialized-patterns.md](./references/specialized-patterns.md) for the template.
