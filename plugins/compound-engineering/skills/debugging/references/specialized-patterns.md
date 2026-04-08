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

## Postmortem

After resolving non-trivial bugs, document a lightweight postmortem:

1. **Timeline**: when introduced, when detected, when resolved (include commit SHAs)
2. **Root cause**: one sentence -- the actual cause, not the symptom
3. **Impact**: what broke, for how long, who was affected
4. **Fix**: what changed and why this fix addresses the root cause
5. **Prevention**: what test, monitor, or process change prevents recurrence

## Signals You're Off Track

Watch for these signs from the user -- they indicate you've left the systematic process:

- "Is that not happening?" -- you assumed behavior without checking
- "Will it show us...?" -- you're not gathering enough evidence
- "Stop guessing" -- you're proposing fixes without root cause
- "We're going in circles" -- same hypothesis repackaged, not a new approach
- Repeating the same type of fix with slight variations -- that's not a new hypothesis
