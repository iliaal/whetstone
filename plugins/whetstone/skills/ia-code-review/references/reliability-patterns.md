# Reliability Patterns

Review lens for operational resilience: what happens when things go wrong at runtime.

## Error Handling Completeness

- **Swallowed errors**: empty `catch` blocks, `.catch(() => {})`, bare `except: pass`. Every error must be logged, re-thrown, or explicitly documented as intentional.
- **Partial error handling**: catching at the top but not handling failures from intermediate steps. If step 2 of 5 fails, are steps 1's side effects cleaned up?
- **Error type specificity**: catching broad exception types (`Exception`, `Error`) when only specific failures are expected. Broad catches mask unexpected bugs.
- **Error context stripping**: re-throwing without the original cause/stack. Wrap, don't replace.

## Timeout and Cancellation

- **Unbounded external calls**: HTTP requests, DB queries, queue operations, file I/O without timeouts. Every external call must have an explicit timeout.
- **Timeout propagation**: if a request has a 30s timeout but calls three services sequentially, each needs a fraction of the budget, not the full 30s.
- **Cancellation handling**: long-running operations should respect cancellation signals (AbortController, context cancellation, CancellationToken). Check whether in-flight work is abandoned or cleaned up.

## Retry Logic

- **Retry without a safety proof**: retrying a non-idempotent operation (payment charge, email send) causes duplicates. Before adding retry logic, verify one of two proofs: write idempotency (a key or natural idempotence), or retry isolation to the pre-write phase. The second is why a missing idempotency key is not automatically a defect: retry is safe under two conditions that must both hold and both be traced — every transient-prone step (download, external enrichment, lookup) runs *before* the write phase, and the write phase never lets a transient-classifiable exception escape, its layers catching and returning status values instead of raising. Then a retry can only have been triggered from a pre-write step, with nothing yet written to duplicate; a partial write simply stays partial. Verify layer by layer from the I/O call outward; a single un-swallowed transient-prone call sitting after a partial write is the whole bug, and the code comment asserting isolation is only as good as the isolation.
- **Retry without backoff**: immediate retries under failure just amplify load. Use exponential backoff with jitter.
- **Unbounded retries**: max attempts must be finite. Infinite retry loops become resource exhaustion.
- **Retry surface**: retry at the right layer. Retrying an entire transaction because one HTTP call failed wastes work. Retry the call, not the transaction.
- **Double retry (stacked retry layers)**: application `@retry` wrapping a client SDK that already auto-retries multiplies attempts (3×3 = 9) and the backoff compounds — a nominal 5s timeout becomes 30s+. Audit the client's default retry policy before wrapping it. Retry at exactly one layer: if the SDK retries, configure its policy; do not add another `@retry` on top. The no-wrapper case needs the same audit: an SDK's `timeout` is normally **per attempt**, and several SDKs default to non-zero built-in retries, so a single call with `timeout=T` has a worst case near `T × (retries + 1)` plus backoff even with no application-level retry around it. "Bounded" is true; a claimed hard ceiling on an interactive path is not. Require `max_retries=0` plus the per-attempt timeout, or an outer deadline.

## Post-Commit External Writes

- **After-commit external mutation is a one-way valve.** Moving an object-store copy, search-index update, or third-party webhook out of the database transaction into an after-commit hook closes "external work done, transaction rolled back" and opens the inverse: the row is committed, the external op fails, and there is no transaction to roll back, no retry, and no reconciler — the row now advertises a state the external store does not hold. Ask three questions: does the committed write encode an invariant that depends on the external op succeeding; is the external op retried on failure (an inline after-commit closure is not); and does anything detect divergence. Escalating to a queued job with retries is necessary but not sufficient — without a terminal-failure handler that reverts the precondition and clears any in-flight flag, you have replaced "lost immediately" with "lost after N retries" while the row still claims the invariant.

## Circuit Breakers

When calling a flaky upstream service:
- **Missing circuit breaker**: repeated calls to a failing service waste resources and slow everything downstream. Open the circuit after N consecutive failures, half-open to probe recovery.
- **No fallback**: when the circuit is open, what happens? Graceful degradation (cached data, default response, feature flag) beats a 500 error.

## Resource Cleanup

- **Connection/handle leaks on error paths**: DB connections, file handles, locks acquired in try blocks must be released in finally/defer/context manager. Check BOTH success and error paths.
- **Pool exhaustion**: if connections are acquired but not returned on timeout or error, the pool drains over time. This is a slow-burn production incident.
- **Subscription leaks**: event listeners, WebSocket connections, pub/sub subscriptions registered without corresponding unsubscribe on teardown.

## Queue and Job Resilience

- **No dead letter queue**: failed jobs that exceed retry limits must go somewhere observable, not disappear silently.
- **No job idempotency**: workers may receive the same message twice (at-least-once delivery). The handler must be safe to re-execute.
- **Missing visibility timeout**: if a worker crashes mid-processing, the message must become available again within a bounded time.

## Detection Patterns

Grep-able signals that often indicate reliability gaps:

```
# Empty catch blocks
catch\s*\([^)]*\)\s*\{\s*\}
except:?\s*$\n\s*pass

# HTTP calls without timeout
fetch\(.*\)(?!.*timeout)
requests\.(get|post|put|delete)\((?!.*timeout)
axios\.(get|post|put|delete)\((?!.*timeout)

# Retry without backoff
retry.*max.*(?!.*backoff|delay|sleep|wait)
```
