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
