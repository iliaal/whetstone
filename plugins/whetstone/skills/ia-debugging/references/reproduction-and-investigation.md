# Reproduction and investigation

Read when establishing a reproducer, reducing a failure, instrumenting a path, or reconciling contradictory evidence. For baseline/build comparisons, also use the dedicated baseline reference.

**0. Read the error.** Read the full error message, stack trace, and line numbers before doing anything. Error messages frequently contain the exact fix. Don't skim; read the entire output.

**Read the totals before the matches.** A grep for failures shows only the failures matching the pattern, and a tool printing a capped sample prints the cap while the real count sits elsewhere. A hypothesis built on "only 8 failed" when the summary says 89 aims every later step at the wrong target. Find the tally line first and compare the sample size against the total.

**After a session resume or compaction, confirm HEAD before trusting file content carried in context.** Context survives compaction; the repository does not freeze while it does. A file body, class shape, or pipeline order in context describes the tree at the moment it was read, and commits from another session, a background agent, a teammate, or your own earlier push can have landed since, with nothing marking the drift. Run `git log --oneline -1` as the first call after any resume and compare it to the SHA the context assumes. Tells that HEAD moved: a deterministic count changes with no cause (test count, symbol count, file count), an edit's `old_string` is missing from a file you "just read", or a constant you remember is absent from it. Re-read a file before editing it after a resume; that is the only way staleness tracking engages.

**1. Reproduce**: build the cheapest feedback loop that exercises the reported failure. Prefer a deterministic broken/fixed signal; for intermittent failures, record conditions, attempts, and observed frequency. A finite run without failure does not prove a race or platform-dependent defect absent.

**Match the exact reported symptom, not a nearby one.** The loop is not reproduction until it fails with the same error text or the same failing assertion the report names. A different exception, a different failing test, or a generic error on the same feature is a different bug wearing the same file path. Treating it as the same defect sends every later step against the wrong target.

**A loop already provided? Run it before touching source.** If the workspace has a test file, or the report says "run X to see the failure," that command *is* the feedback loop: run it after Step 0 and record the RED output before reading source, forming hypotheses, or editing. Without an observed failing run this session, nothing proves the fix changed anything.

Pick the cheapest loop that triggers the bug:

- Failing test (preferred; becomes the regression test in step 6)
- `curl` script or `httpie` invocation against a local server
- CLI harness or REPL session
- Headless browser script (Playwright, Puppeteer)
- Throwaway harness in `/tmp/` (delete when done)
- Any other scripted signal: a property-based test, log replay against a captured request body, or a manual bash session with documented reproduction steps (human-in-the-loop)

If the bug is intermittent, use a bounded run under relevant stress or simulated conditions. If it does not trigger, report the limit and investigate traces, dumps, or static paths without claiming reproduction.

**Cannot build a loop?** State exactly what is missing: access, credentials, artifacts, or repro steps. Continue independent source and artifact investigation, distinguishing observed facts from hypotheses and untested behavior. Ask for material missing input through the active harness's supported question tool (AskUserQuestion in Claude Code, request_user_input in Codex where appropriate), otherwise in chat. A subagent reports the missing input to its orchestrator.

**2. Form initial hypotheses**: form 2-3 hypotheses from the reproduction before investigating broadly: the most likely causes given the symptoms. This focuses investigation on plausible paths. Cite **at least one concrete observation** per hypothesis: a runtime value, a log line, a boundary capture, a behavior delta against a working case, or a specific code reference. "X seems off" is not evidence; "X is null at line 42 because Y never ran under condition Z" is. A hypothesis without a grounding observation is theorizing; instrument until there is a signal (extend the Step 1 loop, or add Step 4 boundary captures).

**3. Reduce**: strip the reproduction to the minimal failing case. Remove unrelated code, data, and configuration until removing one more piece makes the bug disappear. That remaining piece is the trigger.

**4. Investigate**: trace the failing path far enough to explain the violated invariant and the conditions that cause it ([root-cause-tracing.md](./root-cause-tracing.md): stack instrumentation, test pollution detection). Compare code version, data, environment, timing, and configuration in working versus broken cases. Capture relevant environment state with [collect-diagnostics.sh](../scripts/collect-diagnostics.sh). A causal explanation may span several layers or be local to one expression; neither the earliest observed divergence nor a fixed number of stack levels proves root cause.

**Route the first move by bug class before instrumenting.** Visual/rendering bugs want a static read of the render path and computed styles, not logs; behavioral/async/state/lifecycle bugs want a probe added *now* as part of the hypothesis; pure-logic bugs need only a careful read. Before adding any probe, state the yes/no question it answers and the decision rule. CI check failed? See [specialized-patterns.md](./specialized-patterns.md) for the CI-failure workflow (and full routing detail).

**A uniform probe result is a claim about the probe, not about the mechanism.** The smallest inputs that express the shape are also the usual way to measure something else: a normalization step or an empty-input short-circuit upstream can decide the output for every case. Print the intermediate the mechanism itself emits, choose inputs where every other mechanism is non-degenerate, and keep the uniform case in the same run as a control.

**Multi-component systems** (CI -> build -> deploy, API -> service -> DB): before proposing fixes, log what data enters and exits each component boundary and verify env/config propagation across it. Run once to see WHERE it breaks, then investigate that component. Write probes unbuffered to stderr (`console.error`, `fwrite(STDERR, ...)`, `print(..., file=sys.stderr)`); application loggers may be suppressed in tests. Log BEFORE the dangerous operation, not after it fails. Include context: cwd, env vars, `new Error().stack`.

**When two evidence sources contradict and one is executable, execute it.** A comment against the code, a docstring against the callee, a recorded observation against the current build: recency and authorship are not tie-breakers, and weighing them settles nothing. Whichever side can become a command settles it in one pass. Once "one of these is stale" is written down, the next action is the probe.

**Three completeness checks live in [specialized-patterns.md](./specialized-patterns.md):** branches sharing a destination can hide different causes, build-variant differences can expose latent source defects, and both confirming and refuting probes need valid controls.
