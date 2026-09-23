# Repair, escalation, and diagnostic traps

Read when implementing a remedy, assessing a failed experiment, or deciding whether to stop and reassess. Diagnosis-only work remains read-only.

**5. Hypothesize and test**: one change at a time. If a hypothesis is wrong, fully revert before testing the next. Use `git bisect` to pinpoint the exact commit that introduced a regression. **Scope lock**: after forming a hypothesis, identify the narrowest affected directory or file set; do not edit code outside that scope during the debug session. If the fix requires changes elsewhere, update the hypothesis first.

**6. Fix and verify**: create a failing test FIRST, then fix. Run the test. Confirm the original reproduction case passes. No completion claims without fresh verification evidence (see `ia-verification-before-completion`).

**No reachable seam for the bug as it actually triggered** (a race or timing window, hardware- or platform-specific behavior, a defect that only appears against production data) is not license to write a test anyway. A test built around a seam that cannot exercise the real trigger passes for the wrong reason and reads as coverage that does not exist. Record the missing seam as a finding in the Debug Report instead.

**Reproduce-passes is not fixed.** The bad state is often still reachable from a nearby variant when the fix landed at the crash site, not the root cause. Before declaring done, run the **bypass self-check**: name one input variation that reaches the same bad state without tripping the change. If one exists, the fix is at the wrong layer; return to root cause. **Suppression is not a fix**, and the check assumes the fix attacks the bug: swallowing the error (`try/except: pass`, a blanket catch), disabling the failing assertion, or special-casing the reproduction input hides the signal while the defect lives on (a global swallow even *passes* the bypass check). Change behavior at the root cause, not the symptom. For security-relevant bugs, escalate to an **adversarial re-attack**: a fresh-context agent attacks the patched code ([specialized-patterns.md](./specialized-patterns.md)).

**Trim to the minimal diff.** After the fix verifies, simplify to the smallest change that fixes the root cause, ideally as a fresh-context pass ([specialized-patterns.md](./specialized-patterns.md)).

**On a failed fix:** return to Step 5 and identify what the result actually tests: the causal hypothesis, the remedy, the exercised trigger, or the build identity. Reject or revise the hypothesis when the evidence contradicts it; an incomplete remedy does not itself disprove the cause. Change a named variable before another experiment. The Three-Fix Threshold counts complete hypothesis-test cycles.

## Three-Fix Threshold

After 3 failed fix attempts, stop editing and reassess. The count is a retry budget, not evidence of an architectural cause. An attempt = one complete hypothesis-test cycle (form hypothesis, make minimal change, verify). Then:

1. Stop editing.
2. Re-read the failing code path end-to-end instead of spot-checking, questioning assumptions about how the system works.
3. Write down which assumption each failed fix relied on.
4. Escalate with those findings via the ask mechanism in Step 1 (subagents with no user channel: record them in the final report).

In diagnosis-only work, the equivalent budget is 3 investigation cycles without narrowing the component under suspicion; emit interim findings and the next instrumentation step instead of continuing.

**When reasoning reaches the same contradiction twice, instrument it.** Re-deriving the same impossible conclusion from the source is not a new cycle (it produces no edit, so it never trips the threshold), and it is the signal that a value in the mental model is wrong. Log the two divergent values side by side at the point they disagree. One build usually collapses what repeated re-reading cannot.

**Architectural problem indicators** (signals the bug is structural, not a surface fix): each fix reveals unexpected shared state or coupling; fixes require massive refactoring to implement correctly; each fix creates new symptoms elsewhere in the system.

**No root cause found:** if investigation is exhausted without a clear root cause, say so explicitly. Document what was checked, what was ruled out, and what instrumentation to add for next occurrence. An honest "unknown" with good diagnostics beats a fabricated cause.

## Escalation: Competing Hypotheses

When the cause is unclear across multiple components, use Analysis of Competing Hypotheses: generate hypotheses across failure categories, collect evidence FOR and AGAINST each, rank by confidence, investigate the strongest first. Full methodology in [competing-hypotheses.md](./competing-hypotheses.md).

## Pattern Comparison

When the cause isn't obvious, compare the failing path with a working reference and test relevant differences in code, inputs, state, timing, and environment. Similar source may behave differently because of undefined behavior or hidden state; neither a visible difference nor identical code settles causality alone.

## Specialized Patterns

In [specialized-patterns.md](./specialized-patterns.md) unless noted:

- **Intermittent issues**: races, deadlocks, resource exhaustion, timing. Key signals: shared mutable state, check-then-act, circular lock acquisition, pool exhaustion under load.
- **Performance regressions**: slow, latency, or throughput symptoms. Measure a numeric baseline before reading code for the cause.
- **Defense-in-depth validation**: after fixing, validate at every layer, not just where the bug appeared: [defense-in-depth.md](./defense-in-depth.md).
- **Common bug patterns and triage**: async ordering, stale state, stale build artifacts, recurring fix site; severity-vs-priority triage.
- **Off-track signals**: user phrases ("stop guessing", "we're going in circles") that mean the systematic process was abandoned.

## Anti-Patterns and Red Flags

When you catch yourself doing or thinking these things, **stop and return to Step 1 (Reproduce)**:

| What You're Doing / Thinking | What It Really Means |
|-----------------------------|---------------------|
| Shotgun debugging / "I see the problem, let me fix it" / "It's probably X" | Reasoning is not evidence. Form a hypothesis, make one change, test, revert if wrong. Trace the actual execution path. |
| Ignoring intermittent failures ("works on my machine") | Instrument and reproduce under load. Isolation success doesn't explain integration failure. |
| "I'll clean up the debugging later" | Remove diagnostic code now or it ships to production. |
| "This failure is pre-existing, not related to our changes" | Prove it: run the test suite on the base branch. No receipts = no claim. |
| "The tool truncated the output" / "the runner must be broken" | Check local state first: a moved HEAD, a stale context, or a dirty tree explains this far more often than tool misbehavior. Proving a tool bug means reproducing it at a known commit. A report filed from stale context wastes the fix and costs the tool its credibility for the next session. |
| "The test is wrong, not the code" | Verify before dismissing. Read the test's intent. If the test is genuinely wrong, fix it with a clear rationale, not a silent update. |
| "Reference too long, I'll adapt the pattern" | Partial understanding guarantees bugs. Read the working example completely and apply it exactly. |
| "The experiment came back negative, so the hypothesis is dead" | A bounded experiment bounds itself first. State the coverage the run achieved before a negative retires a hypothesis. |
| "I falsified the trigger, so that area is ruled out" | Falsifying one trigger of a mechanism does not falsify the mechanism. Re-test through a different trigger. |

## Verify

- Causal conclusion supported by source/runtime evidence, or the remaining uncertainty explicitly reported
- For repaired bugs with a reachable test seam, regression test fails without the fix and passes with it; otherwise report the verification used and the missing seam
- Bypass self-check run: no variant input reaches the same bad state without tripping the fix (for security-relevant fixes, adversarial re-attack found no bypass)
- Debug Report emitted with all seven fields (SYMPTOM, ROOT CAUSE, FIX, EVIDENCE, REGRESSION, RELATED, STATUS)
- No diagnostic instrumentation left in code (`git diff` shows no leftover logging)
