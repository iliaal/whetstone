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

## Process

**0. Read the error.** Read the full error message, stack trace, and line numbers before doing anything. Error messages frequently contain the exact fix. Don't skim -- read the entire output.

**After a session resume or compaction, confirm HEAD before trusting file content carried in context.** Context survives compaction; the repository does not freeze while it does. A file body, class shape, or pipeline order in context describes the tree at the moment it was read, and commits from another session, a background agent, a teammate, or your own earlier push can have landed since -- nothing marks the drift. Run `git log --oneline -1` as the first call after any resume and compare it to the SHA the context assumes. Tells that HEAD moved: a deterministic count changes with no cause (test count, symbol count, file count), an edit's `old_string` is missing from a file you "just read", or a constant you remember is absent from it. Re-read a file before editing it after a resume; that is the only way staleness tracking engages.

**1. Reproduce** -- build a feedback loop, *then* make the bug consistent. The loop is the deliverable of this step, not the analysis. Without a fast, deterministic "broken / fixed" signal, every later step is guesswork.

**Match the exact reported symptom, not a nearby one.** The loop is not reproduction until it fails with the same error text or the same failing assertion the report names -- a different exception, a different failing test, or a generic error on the same feature is a different bug wearing the same file path. Treating it as the same defect sends every later step against the wrong target.

**A loop already provided? Run it before touching source.** If the workspace has a test file, or the report says "run X to see the failure," that command *is* the feedback loop: run it after Step 0 and record the RED output before reading source, forming hypotheses, or editing -- without an observed failing run this session, nothing proves the fix changed anything.

Pick the cheapest loop that triggers the bug:

- Failing test (preferred -- becomes the regression test in step 6)
- `curl` script or `httpie` invocation against a local server
- CLI harness or REPL session
- Headless browser script (Playwright, Puppeteer)
- Throwaway harness in `/tmp/` -- delete when done
- Any other scripted signal: a property-based test, log replay against a captured request body, or a manual bash session with documented reproduction steps (human-in-the-loop)

If the bug is intermittent, run the loop N times under stress or simulate poor conditions (slow network, low memory) until it triggers reliably.

**Cannot build a loop?** State exactly what is missing -- access, credentials, artifacts, repro steps. Ask via AskUserQuestion (Claude Code; load with ToolSearch `select:AskUserQuestion` if not loaded) or request_user_input (Codex); fall back to numbered options in chat. Investigating without a signal is pattern-matching, not debugging. As a subagent with no user channel, record the missing items in the final report and continue with static analysis, labeling all output unverified.

**2. Form initial hypotheses** -- form 2-3 hypotheses from the reproduction before investigating broadly: the most likely causes given the symptoms. This focuses investigation on plausible paths. Cite **at least one concrete observation** per hypothesis: a runtime value, a log line, a boundary capture, a behavior delta against a working case, or a specific code reference. "X seems off" is not evidence; "X is null at line 42 because Y never ran under condition Z" is. A hypothesis without a grounding observation is theorizing -- instrument until there is a signal (extend the Step 1 loop, or add Step 4 boundary captures).

**3. Reduce** -- strip the reproduction to the minimal failing case. Remove unrelated code, data, and configuration until removing one more piece makes the bug disappear. That remaining piece is the trigger.

**4. Investigate** -- trace backward through the call chain from the symptom to the original trigger; fix at the source, not where the error surfaces ([root-cause-tracing.md](./references/root-cause-tracing.md): stack instrumentation, test pollution detection). Compare working vs broken state in a differential table across dimensions: code version, data, environment, timing, configuration. Capture environment state with [collect-diagnostics.sh](./scripts/collect-diagnostics.sh) for the comparison or for bug reports. Root cause = the earliest point where behavior diverged from expectation, with evidence two levels deep: not "it failed here" but "it failed here because X was null, and X was null because Y never set it".

**Route the first move by bug class before instrumenting.** Visual/rendering bugs want a static read of the render path and computed styles, not logs; behavioral/async/state/lifecycle bugs want a probe added *now* as part of the hypothesis; pure-logic bugs need only a careful read. Before adding any probe, state the yes/no question it answers and the decision rule. CI check failed? See [specialized-patterns.md](./references/specialized-patterns.md) for the CI-failure workflow (and full routing detail).

**Multi-component systems** (CI -> build -> deploy, API -> service -> DB): before proposing fixes, log what data enters and exits each component boundary and verify env/config propagation across it. Run once to see WHERE it breaks, then investigate that component. Write probes unbuffered to stderr (`console.error`, `fwrite(STDERR, ...)`, `print(..., file=sys.stderr)`); application loggers may be suppressed in tests. Log BEFORE the dangerous operation, not after it fails. Include context: cwd, env vars, `new Error().stack`.

**Pre-existing failure proof:** before claiming a test failure is "not related to our changes," prove it: run `git stash && [test command]` to confirm the failure exists on the base branch. Pre-existing without receipts is a lazy claim. The stash stack is shared across linked worktrees, so this recipe is unsafe in a tree that automation or a background agent also touches -- there, take a scratch copy or a dedicated worktree instead of stashing in place.

**A cross-branch A/B needs a pristine baseline.** `git checkout <baseline>` does not discard a dirty working-tree edit that merges cleanly -- it carries it into the checked-out tree, so the "before" build silently contains the fix and the experiment runs patched-vs-patched. The tell is *before == after* to the byte when a delta was expected. Commit the fix on its branch first, then run `git status --porcelain` after the baseline checkout and before the baseline build; non-empty output means the comparison is already poisoned. When restoring a single file, name the source (`git checkout HEAD -- <file>` for the commit, `git checkout <base> -- <file>` for the baseline) -- the bare `git checkout -- <file>` restores from the *index*, which may hold neither -- and assert the expected diff before rebuilding.

**Before external searches** (web, docs, forums): strip hostnames, IPs, file paths, SQL fragments, and customer data from the query. Raw stack traces leak privacy and return noise.

**Redaction also applies to what gets shown back, not just what goes out.** This skill has the agent paste commands, probe output, and captured artifacts into the conversation, and those carry credentials -- `Authorization` headers in a captured request, connection strings in a repro command, tokens in an environment dump. Replace each with `<REDACTED>` before it appears. Better, remove the need: build the reproduction loop so every credential is read from the environment (`$API_TOKEN`, `$DATABASE_URL`) rather than typed into the command, which keeps the value out of the transcript entirely, and quote only the lines of a captured artifact that carry signal. If redacting leaves too little to diagnose from, say so and ask for what is missing rather than pasting it raw.

**5. Hypothesize and test** -- one change at a time. If a hypothesis is wrong, fully revert before testing the next. Use `git bisect` to pinpoint the exact commit that introduced a regression. **Scope lock**: after forming a hypothesis, identify the narrowest affected directory or file set; do not edit code outside that scope during the debug session. If the fix requires changes elsewhere, update the hypothesis first.

**6. Fix and verify** -- create a failing test FIRST, then fix. Run the test. Confirm the original reproduction case passes. No completion claims without fresh verification evidence (see `ia-verification-before-completion`).

**No reachable seam for the bug as it actually triggered** (a race or timing window, hardware- or platform-specific behavior, a defect that only appears against production data) is not license to write a test anyway. A test built around a seam that cannot exercise the real trigger passes for the wrong reason and reads as coverage that does not exist. Record the missing seam as a finding in the Debug Report instead.

**Reproduce-passes is not fixed.** The bad state is often still reachable from a nearby variant when the fix landed at the crash site, not the root cause. Before declaring done, run the **bypass self-check**: name one input variation that reaches the same bad state without tripping the change -- if one exists, the fix is at the wrong layer; return to root cause. **Suppression is not a fix**, and the check assumes the fix attacks the bug: swallowing the error (`try/except: pass`, a blanket catch), disabling the failing assertion, or special-casing the reproduction input hides the signal while the defect lives on (a global swallow even *passes* the bypass check). Change behavior at the root cause, not the symptom. For security-relevant bugs, escalate to an **adversarial re-attack**: a fresh-context agent attacks the patched code ([specialized-patterns.md](./references/specialized-patterns.md)).

**Trim to the minimal diff.** After the fix verifies, simplify to the smallest change that fixes the root cause -- best done as a fresh-context pass ([specialized-patterns.md](./references/specialized-patterns.md)).

**On a failed fix:** return to Step 5 and *explicitly invalidate the current hypothesis*: state what evidence ruled it out, then form a new hypothesis with its own grounding observation. Do not retry variants of the same theory ("maybe it was the other branch") -- that is rationalization, not iteration. The Three-Fix Threshold counts cycles, not retries within one broken theory.

## Diagnosis-Only Mode

When the task mandate forbids edits or builds ("DIAGNOSIS ONLY", "do NOT edit", read-only investigation, another process owns the build): run Steps 0-4 only. Emit the Debug Report with FIX replaced by "PROPOSED FIX" plus the exact command that would verify it, STATUS=NEEDS_CONTEXT, and every conclusion labeled unverified-hypothesis.

## Debug Report

Emit after every resolved bug. For non-trivial production bugs, also write a lightweight postmortem: timeline, root cause, impact, fix, prevention (template in [specialized-patterns.md](./references/specialized-patterns.md)).

```
SYMPTOM:    [What was observed]
ROOT CAUSE: [Why it happened -- file:line with evidence]
FIX:        [What changed]
EVIDENCE:   [Verification output proving the fix]
REGRESSION: [Test added to prevent recurrence]
RELATED:    [Prior bugs in same area, known issues, architectural notes]
STATUS:     DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT (DONE = fix verified | DONE_WITH_CONCERNS = verified, residual risk noted | BLOCKED = blocker stated | NEEDS_CONTEXT = missing information named)
```

## Three-Fix Threshold

After 3 failed fix attempts, STOP -- the problem is likely architectural, not a surface bug. An attempt = one complete hypothesis-test cycle (form hypothesis, make minimal change, verify). Then:

1. Stop editing.
2. Re-read the failing code path end-to-end instead of spot-checking, questioning assumptions about how the system works.
3. Write down which assumption each failed fix relied on.
4. Escalate with those findings via the ask mechanism in Step 1 (subagents with no user channel: record them in the final report).

In diagnosis-only work, the equivalent budget is 3 investigation cycles without narrowing the component under suspicion -- emit interim findings and the next instrumentation step instead of continuing.

**When reasoning reaches the same contradiction twice, instrument it.** Re-deriving the same impossible conclusion from the source is not a new cycle -- it produces no edit, so it never trips the threshold -- and it is the signal that a value in the mental model is wrong. Log the two divergent values side by side at the point they disagree. One build usually collapses what repeated re-reading cannot.

**Architectural problem indicators** -- signals the bug is structural, not a surface fix: each fix reveals unexpected shared state or coupling; fixes require massive refactoring to implement correctly; each fix creates new symptoms elsewhere in the system.

**No root cause found:** if investigation is exhausted without a clear root cause, say so explicitly. Document what was checked, what was ruled out, and what instrumentation to add for next occurrence. An honest "unknown" with good diagnostics beats a fabricated cause.

## Escalation: Competing Hypotheses

When the cause is unclear across multiple components, use Analysis of Competing Hypotheses: generate hypotheses across failure categories, collect evidence FOR and AGAINST each, rank by confidence, investigate the strongest first. Full methodology in [competing-hypotheses.md](./references/competing-hypotheses.md).

## Pattern Comparison

When the cause isn't obvious, find working similar code and compare it structurally with the broken path. Read the working reference completely -- don't skim -- and list every difference, however small; don't assume any difference can't matter. The bug is in one of them.

## Specialized Patterns

In [specialized-patterns.md](./references/specialized-patterns.md) unless noted:

- **Intermittent issues** -- races, deadlocks, resource exhaustion, timing. Key signals: shared mutable state, check-then-act, circular lock acquisition, pool exhaustion under load.
- **Performance regressions** -- slow, latency, or throughput symptoms. Measure a numeric baseline before reading code for the cause.
- **Defense-in-depth validation** -- after fixing, validate at every layer, not just where the bug appeared: [defense-in-depth.md](./references/defense-in-depth.md).
- **Common bug patterns and triage** -- async ordering, stale state, stale build artifacts, recurring fix site; severity-vs-priority triage.
- **Off-track signals** -- user phrases ("stop guessing", "we're going in circles") that mean the systematic process was abandoned.

## Anti-Patterns and Red Flags

When you catch yourself doing or thinking these things, **stop and return to Step 1 (Reproduce)**:

| What You're Doing / Thinking | What It Really Means |
|-----------------------------|---------------------|
| Shotgun debugging / "I see the problem, let me fix it" / "It's probably X" | Reasoning is not evidence. Form a hypothesis, make one change, test, revert if wrong. Trace the actual execution path. |
| Ignoring intermittent failures ("works on my machine") | Instrument and reproduce under load. Isolation success doesn't explain integration failure. |
| "I'll clean up the debugging later" | Remove diagnostic code now or it ships to production. |
| "This failure is pre-existing, not related to our changes" | Prove it: run the test suite on the base branch. No receipts = no claim. |
| "The tool truncated the output" / "the runner must be broken" | Check local state first -- a moved HEAD, a stale context, or a dirty tree explains this far more often than tool misbehavior. Proving a tool bug means reproducing it at a known commit. A report filed from stale context wastes the fix and costs the tool its credibility for the next session. |
| "The test is wrong, not the code" | Verify before dismissing. Read the test's intent. If the test is genuinely wrong, fix it with a clear rationale, not a silent update. |
| "Reference too long, I'll adapt the pattern" | Partial understanding guarantees bugs. Read the working example completely and apply it exactly. |

## Verify

- Root cause identified with `file:line` evidence (not just "it failed here")
- Regression test exists and fails without the fix, passes with it
- Bypass self-check run: no variant input reaches the same bad state without tripping the fix (for security-relevant fixes, adversarial re-attack found no bypass)
- Debug Report emitted with all seven fields (SYMPTOM, ROOT CAUSE, FIX, EVIDENCE, REGRESSION, RELATED, STATUS)
- No diagnostic instrumentation left in code (`git diff` shows no leftover logging)
