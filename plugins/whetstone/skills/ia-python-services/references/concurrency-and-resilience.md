# Concurrency and resilience

## Parallelism

| Workload | Approach |
|----------|----------|
| Many concurrent I/O calls | `asyncio` (gather, create_task) |
| CPU-bound computation | `multiprocessing.Pool` or `concurrent.futures.ProcessPoolExecutor` |
| Mixed I/O + CPU | `asyncio.to_thread()` to offload blocking work |
| Simple scripts, few connections | Stay synchronous |

### Sync vs Async Decision

**Use async (asyncio) when:**
- I/O-bound work has multiple concurrent operations (HTTP calls, database queries, file I/O happening in parallel)
- WebSocket servers or long-lived connections require it
- The framework requires it (FastAPI async endpoints, aiohttp)

**Stay synchronous when:**
- Work is CPU-bound (computation, data transformation) -- async adds nothing, use multiprocessing instead
- Building simple scripts and CLI tools with sequential I/O
- All I/O is sequential anyway (one DB query, process result, one API call)
- The team lacks async debugging experience (asyncio stack traces are harder to read)

**Rule of thumb:** if the code is not waiting on multiple I/O operations concurrently, sync is simpler and correct. Do not add async complexity for a single sequential pipeline.

**Key rule:** Stay fully sync or fully async within a call path.

**asyncio patterns:**
- `asyncio.gather(*tasks)` for concurrent I/O -- use `return_exceptions=True` for partial failure tolerance
- `asyncio.TaskGroup` (3.11+) for structured concurrency -- automatic cancellation of sibling tasks on failure; prefer over `gather` when all tasks must succeed
- A bare `asyncio.create_task(...)` whose result is discarded can vanish mid-flight: the event loop holds only a weak reference, so an unreferenced task may be garbage-collected before it finishes, and any exception it raised is swallowed with at most a "Task exception was never retrieved" warning. Keep a strong reference (`_bg = set()`; `t = asyncio.create_task(c)`; `_bg.add(t)`; `t.add_done_callback(_bg.discard)`) or use `TaskGroup`, which holds its children until they finish
- `asyncio.Semaphore(n)` to limit concurrency (rate limiting external APIs)
- `asyncio.wait_for(coro, timeout=N)` for timeouts
- `asyncio.Queue` for producer-consumer
- `asyncio.Lock` when coroutines share mutable state
- Never block the event loop: `asyncio.to_thread(sync_fn)` for sync libs, `aiohttp`/`httpx.AsyncClient` for HTTP
- Handle `CancelledError` -- always re-raise after cleanup
- Async generators (`async for`) for streaming/pagination

**multiprocessing** for CPU-bound:
```python
from concurrent.futures import ProcessPoolExecutor
with ProcessPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(cpu_task, items))
```

See [fastapi.md](./fastapi.md) for project structure, lifespan, config, DI, async DB, and repository pattern.


## Background Jobs

- Return job ID immediately, process async. Client polls `/jobs/{id}` for status
- **Celery**: `@app.task(bind=True, max_retries=3, autoretry_for=(ConnectionError,))` -- exponential backoff: `raise self.retry(countdown=2**self.request.retries * 60)`
- **Alternatives**: Dramatiq (modern Celery), RQ (simple Redis), cloud-native (SQS+Lambda, Cloud Tasks)
- **Idempotency is mandatory** -- tasks may retry. Use idempotency keys for external calls and atomic upserts for writes (`ON CONFLICT DO UPDATE`, `INSERT ... ON DUPLICATE KEY UPDATE`). A read-then-write pair is not idempotent under concurrent retry: two workers both read "absent" and both insert. Uniqueness has to be enforced by a database constraint, not by the preceding read
- Dead letter queue for permanently failed tasks after max retries
- Task workflows: `chain(a.s(), b.s())` for sequential, `group(...)` for parallel, `chord(group, callback)` for fan-out/fan-in


## Resilience

**Retries with tenacity:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type

@retry(
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    stop=stop_after_attempt(5) | stop_after_delay(60),
    wait=wait_exponential_jitter(initial=1, max=30),
    before_sleep=log_retry_attempt,
)
def call_api(url: str) -> dict: ...
```

- Retry only transient errors: network, 429/502/503/504. Never retry 4xx (except 429), auth errors, validation errors
- Every network call needs a timeout
- `@fail_safe(default=[])` decorator for non-critical paths -- return cached/default on failure. **Never on a path where the call is the security decision** (authz check, trust score, entitlement or license gate): there the default has to be deny, and a `default=[]` or `default=None` that a caller reads as "no restrictions" is a fail-open with a decorator on it. Any fail-open allowance scopes to transport failure alone -- `ConnectError`, `ConnectTimeout`. A response that arrived but cannot be trusted (4xx/5xx, malformed JSON, a body that fails schema validation, an unrecognized verdict string) stays denied, because the endpoint was reached and did not answer. Same for a "no record yet" state: reject by default, allow only through an explicit onboarding opt-in
- `functools.lru_cache(maxsize=N)` for pure-function memoization; `functools.cache` (unbounded) for small domains
- Stack decorators: `@traced @with_timeout(30) @retry(...)` -- separate infra from business logic

**Connection pooling** is mandatory for production: reuse `httpx.AsyncClient()` across requests, configure SQLAlchemy `pool_size`/`max_overflow`, use `aiohttp.TCPConnector(limit=N)`.

- **Switching to a shared pooled `requests.Session` newly exposes stale keep-alive failures.** Module-level `requests.get`/`requests.post` build a fresh `Session` and connection pool per call, so a dead or half-closed socket can never be served; a process-wide `Session` reuses keep-alive connections, and urllib3 does not liveness-probe one before reuse. When an LB or NAT has silently dropped an idle socket (an ALB's default idle timeout is 60s), the next reuse raises `ConnectionError` wrapping urllib3 `ProtocolError` / `http.client.RemoteDisconnected` -- and under `HTTPAdapter(max_retries=0)`, chosen to "keep behavior unchanged", it reaches the caller unretried. That claim is true of *response* semantics (status, timeouts, body) and false of *connection-failure* semantics. It bites hardest during traffic lulls, when the connection has been idle past the LB timeout
- **`Retry(connect=1)` does not cover a stale keep-alive** -- wrong layer. urllib3 routes errors by class and a stale socket is a *read*/protocol error: `Retry._is_connection_error(ProtocolError('Connection aborted.', OSError()))` is `False` while `_is_read_error(...)` is `True`, so a connect budget never applies. Covering it needs `read >= 1`, but `Retry.DEFAULT_ALLOWED_METHODS` is `{GET, HEAD, PUT, DELETE, OPTIONS, TRACE}` -- POST and PATCH are excluded, and widening `allowed_methods` retries non-idempotent writes that may already have reached the server. There is no one-liner that safely covers everything: either scope the retry to idempotent verbs and let writes bubble, or accept the risk deliberately because an outer layer (a queue redelivery that re-runs the whole unit of work) self-heals it -- and then stop claiming the behavior is unchanged. Before prescribing any HTTP-retry config, name the exact exception class, map it through `_is_connection_error`/`_is_read_error`, and check `allowed_methods` against the verbs actually in use


## Production Resilience

- **Fail-fast config validation**: use a Pydantic `BaseSettings` model with `model_validator` to parse and validate all environment variables at startup. If invalid, crash before serving traffic. Never discover a missing secret on the first request that needs it.
- **Health endpoints**: expose `/health` (shallow liveness -- returns 200 if the process responds) and `/ready` (deep readiness -- verifies database, Redis, and critical dependencies are reachable). Load balancers route traffic based on `/ready`; orchestrators restart based on `/health`.
