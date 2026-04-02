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

- **Retry without idempotency**: retrying a non-idempotent operation (payment charge, email send) causes duplicates. Verify idempotency before adding retry logic.
- **Retry without backoff**: immediate retries under failure just amplify load. Use exponential backoff with jitter.
- **Unbounded retries**: max attempts must be finite. Infinite retry loops become resource exhaustion.
- **Retry surface**: retry at the right layer. Retrying an entire transaction because one HTTP call failed wastes work. Retry the call, not the transaction.

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
