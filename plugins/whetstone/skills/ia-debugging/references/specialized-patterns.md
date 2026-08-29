# Specialized Debugging Patterns

## Environment Diagnostics

Before investigating, capture the environment state using [collect-diagnostics.sh](../scripts/collect-diagnostics.sh):

```bash
bash collect-diagnostics.sh           # print to stdout
bash collect-diagnostics.sh diag.md   # write to file
```

Collects system info, language versions, git state, project files, and environment variables. Use during differential analysis to compare working vs broken environments, or attach to bug reports.

## Intermittent Issues

- Track with correlation IDs across distributed components
- Race conditions: look for shared mutable state, check-then-act patterns, missing locks. In async code (Node.js, Python asyncio): interleaved `.then()` chains, unguarded shared state between concurrent tasks, missing transaction isolation in DB operations
- Deadlocks: check for circular lock acquisition (DB row locks held across multiple queries), circular `await` dependencies in async code, connection pool exhaustion blocking queries that would release other connections
- Resource exhaustion: monitor memory growth, connection pool depletion, file descriptor leaks. Under load: check pool size vs concurrent request count, verify connections are returned on error paths (finally/dispose)
- Timing-dependent: replace arbitrary `sleep()` with condition-based polling -- wait for the actual state, not a duration

## CI Failures

When a CI check fails on a PR or branch:

1. **Fetch logs**: `gh run view <run_id> --log` (extract run ID from the checks URL). If `detailsUrl` points to a non-GitHub provider (Buildkite, CircleCI), don't attempt to fetch logs -- report the URL and let the user investigate.
2. **Classify the failure**: build error (compilation/dependency), test failure (which test, what assertion), lint/type error (which rule, which file), timeout (which step exceeded limits), or infrastructure (runner OOM, network, flaky service).
3. **Reproduce locally**: run the same command from the CI config (`cat .github/workflows/*.yml` to find it). If it passes locally, the issue is environment-specific -- compare CI runner config against local (OS, versions, env vars, caching).
4. **Fix and verify**: fix the issue, then suggest re-running the relevant checks: `gh pr checks <pr> --watch` or `gh run rerun <run_id> --failed`.

Don't retry a CI run without changing something. If the same run failed twice, it's not flaky -- it's broken.

## Post-Fix Passes

- **Adversarial re-attack** (security-relevant fixes): after the bypass self-check, spawn a fresh-context agent, blind to the fix reasoning, and have it attack the patched code to find a variant input that still triggers the bad state. The fixing session cannot attack its own patch objectively -- it knows too much about the intended fix path.
- **Fresh-context trim pass**: after the fix verifies, run a fresh-context pass asked only to "simplify to the smallest change that fixes the root cause." The fixing session is anchored to its own reasoning and over-reaches; a blind pass reliably finds the trim points without reintroducing the bug.

## Postmortem

After resolving non-trivial bugs, document a lightweight postmortem:

1. **Timeline**: when introduced, when detected, when resolved (include commit SHAs)
2. **Root cause**: one sentence -- the actual cause, not the symptom
3. **Impact**: what broke, for how long, who was affected
4. **Fix**: what changed and why this fix addresses the root cause
5. **Prevention**: what test, monitor, or process change prevents recurrence

## Common Bug Patterns

- **Async ordering** -- missing `await`, unhandled promise rejection, callback firing before setup completes. The temporal gap between setup and callback is where bugs hide.
- **Stale state** -- cached values, stale closures, outdated config, old build artifacts. When behavior contradicts the code you're reading, verify you're running what you think you're running.
- **Stale build artifacts** -- a test failure whose source path is provably correct and untouched by your diff is the tell: the source on disk is right, but an incremental build relinked a stale object. A clean working tree (`git status`) does not mean a clean build tree -- build outputs are typically gitignored. Baseline the *build*, not the commit: rebuild from clean (`make clean`, fresh `target/`) before debugging the code. Checking out an old commit inherits the same stale objects and proves nothing.
- **Recurring fix site** -- if `git log` shows 3+ prior fixes in the same file, the file needs redesign, not another patch. Escalate as architectural smell.
- **A metric pinned at a clean extreme** -- an aggregate landing on exactly 0%, 100%, or all-zero across a correlated set is usually the failure path feeding the metric, not a result. Check whether the error handler emits a value the aggregator accepts as real: a type-valid placeholder verdict, a default score, a swallowed exception returning the neutral case. Ask what number comes out when the dependency fails for *every* item at once; if it is indistinguishable from a genuine one, that is the bug. Size- or batch-correlated zeros (small inputs fine, large ones uniformly zero) point at the scoring call raising before it ever ran.
- **Container-local id used as a global key** -- an id minted per parent (row N of a batch, finding N of a review, id 1 within a tenant) collides silently when flattened into one map. If that map feeds a completeness or coverage check, the failure is a *passing* gate rather than a wrong value: the erased information (which parent) is exactly what the check was measuring. Cheapest probe: the keyed map holds fewer entries than the source rows, with no error raised. Put the parent in the key, and make a collision that "cannot happen" assert instead of overwrite.

## First Move by Bug Class

The first debugging move depends on the bug class. "Add logging" is the default reflex, but for some classes it is the wrong first move -- it captures nothing and burns a cycle.

- **Visual / rendering / layout** -- read statically first. Instrumentation cannot capture what the compositor, layout engine, or cascade actually did. Read the render path and inspect computed styles (resolved values, not the source rule) instead of logging. A log fires before paint and says nothing about the rendered result.
- **Behavioral / lifecycle / async / state** -- instrument first, before writing any fix. Add the probe (a log or assertion) as part of forming the hypothesis, not after a fix has already failed. These bugs live in values and ordering that are invisible from a static read; the probe is how the hypothesis becomes observable.
- **Pure logic** (off-by-one, wrong branch, bad comparison) -- a careful static read is sufficient. No instrumentation needed; the defect is on the page once the path is read end to end.

**Write the question before the log.** Before adding any probe, state the yes/no question it answers and pre-commit the decision rule: "if this prints X before Y, hypothesis A survives; if not, A is dead." A log with no question attached is noise -- it produces output, not evidence.

**A log that changes the behavior is itself evidence.** If adding or removing a probe makes the bug appear, disappear, or move, that signals a timing, lifecycle, or concurrency defect -- the observation is perturbing the very ordering that is broken. Do not chase the now-hidden symptom; treat the sensitivity as the lead and investigate the race.

**When the probe kills the repro, switch to non-perturbing capture.** Once two of these hold -- fires under the real harness but not under a debugger, vanishes when print-style logging is added, vanishes under a built-in verbose dump, or crash-or-not flips across rebuilds of identical source -- stop trying I/O-based observation; every heavier tool makes it less reproducible. Record into a preallocated in-memory buffer using plain stores in the hot path (no formatting, no syscalls, no flush) and dump the buffer only from the failure or crash handler, where I/O is free. Keep the instrument behind a single build flag, add a per-entry invocation counter so re-dispatch within one call is distinguishable from a fresh entry, and commit each instrument increment -- shared automation can reset a worktree mid-task and take an uncommitted probe with it.

## Bug Triage

When multiple bugs exist, prioritize by:
- **Severity** (data loss > crash > wrong output > cosmetic) separately from **Priority** (blocking release > customer-facing > internal)
- Reproducibility: always > sometimes > once. "Sometimes" bugs need instrumentation before fixing.
- Quick wins: if a fix is < 5 minutes and unblocks others, do it first

## Signals You're Off Track

Watch for these signs from the user -- they indicate you've left the systematic process:

- "Is that not happening?" -- you assumed behavior without checking
- "Will it show us...?" -- you're not gathering enough evidence
- "Stop guessing" -- you're proposing fixes without root cause
- "We're going in circles" -- same hypothesis repackaged, not a new approach
- Repeating the same type of fix with slight variations -- that's not a new hypothesis
