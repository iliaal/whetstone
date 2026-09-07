# Async operations and production

## Async Patterns

| Pattern | Use When |
|---------|----------|
| `async/await` | Sequential operations |
| `Promise.all` | Parallel independent ops |
| `Promise.allSettled` | Parallel, some may fail |
| `Promise.race` | Timeout or first-wins |

Never use readFileSync or other sync methods in production -- use `fs.promises` or stream equivalents. Offload CPU work to worker threads (Piscina). Stream large payloads.


## Production Resilience

- **Fail-fast env validation**: parse and validate all environment variables at startup with a Zod schema (`const env = envSchema.parse(process.env)`). If invalid, crash before serving traffic. Never discover a missing env var on the first request that needs it.
- **Health endpoints**: expose both `/health` (shallow, always 200 if process is alive) and `/ready` (deep, verifies database, cache, and critical dependencies are reachable). Load balancers probe `/ready` for traffic routing; monitoring probes `/health` for process liveness. Don't conflate them.
- **Caching**: Redis cache-aside for DB/API responses; in-memory LRU with TTL for hot paths. Always invalidate on writes.
- **Load shedding**: `@fastify/under-pressure` (or equivalent) -- monitor event loop delay, heap, RSS; return 503 when thresholds exceeded.
- **Response schemas**: In Fastify, always define response schemas -- enables `fast-json-stringify` for 2-3x faster serialization.
- **Circuit breaker**: use `opossum` for outbound service calls. States: CLOSED (normal) -> OPEN (failing, return fallback) -> HALF_OPEN (probe). Prevents cascade failures when downstream services are down. When the outbound call *is* the security decision (authz check, trust score, license or entitlement gate), the fallback must be **deny**, and any fail-open allowance scopes to transport failure only -- connection refused, DNS failure, timeout. A response that arrived but cannot be trusted (4xx/5xx, malformed JSON, schema-invalid body, unknown verdict value) stays blocked: the endpoint was reached and did not answer. Absence of evidence is not evidence of trust. Same for "no history yet" states -- reject by default, allow only through an explicit onboarding opt-in.
- **Node's global `fetch` (undici) drops long-silent responses.** A request that returns zero bytes for tens of seconds -- a reasoning LLM call, a slow report generator, a buffering gateway -- fails as `Invalid response body ... Premature close` whenever the egress path reaps idle TCP flows (cloud NAT, stateful firewall). `curl` and Node's built-in `https` module survive the identical request on the same box because they keep the flow warm. Rule out the red herrings before redesigning: it fails on the first call of a fresh process (not pool reuse), at concurrency 1 (not concurrency), and with `stream: true` yielding zero chunks (streaming does not help when the upstream buffers before its first byte). An SDK's `httpAgent`/`https.Agent` option is silently ignored once the SDK is on global `fetch`. Route that one request over Node's built-in `https` module with `req.on('socket', s => s.setKeepAlive(true, 10_000))` and an explicit `req.setTimeout(...)`, keeping the request/response contract identical. It works on a laptop and fails only on the deployed box -- reproduce on the host that fails.
- **Guard the empty result set before shipping the artifact.** If every unit in an unattended pipeline failed, alert -- do not emit or email a hollow report. "The call returned without throwing" is not "I have content", and the input-side twin matters equally: a stage fed an empty series should throw rather than pass nothing downstream. Pair it with logging the *real* upstream error on each retry and on final give-up; a wrapper that prints only `attempt N failed` hides the one string ("Premature close" vs "401" vs "timeout") that names the failure class.
- **A loop that reuses one stateful client and swallows a failed navigation attributes stale state to the current key.** `page.goto(url).catch(() => null)` inside a scraper loop parses whatever is still loaded -- the *previous* item's DOM -- and writes the extraction under the *current* item's cache key. Nothing throws, extraction "succeeds", and with a TTL the poisoned row outlives the blip that caused it; a first-item failure caches the landing page as data. Keep the `.catch` for uniform timeout handling but gate the parse and the cache write on post-conditions that confirm the right resource is loaded: the resolved URL contains the item's own path segment (compare case-insensitively -- redirects normalize slug case), and a selector present on every valid target page is in the result (this catches the URL-preserving cases: interstitials, soft-404s, layout changes). Throw on either miss so the existing per-item catch drives retry or skip, and the cache write is unreachable.
- **A listener on a caller-supplied server outlives the module's own teardown.** Closing a server the module created also drops its listeners, but a server passed in by the caller keeps them after the module disposes -- the module must keep the handler reference and call `.off(event, handler)` in its own dispose path. Skip this and the stale listener keeps firing on the shared server, swallowing connections or messages meant for the next instance.


## Observability

- **Define "working" before instrumenting**: write the questions an on-call engineer will ask when this is broken at 3am ("which dependency is timing out?", "is it all users or one tenant?"), then add only the telemetry that answers them. Instrumentation with no question behind it is cost and noise.
- **Pick the signal by the question it answers**: logs = "what happened in this one case?" (high-detail, structured, sampled under load); metrics = "how often / how fast / how saturated?" (cheap aggregates — keep label cardinality bounded, never user IDs or request IDs as labels); traces = "where did the time or the error go across services?".
- **Structured logging**: `pino` with a stable set of event names and a correlation/request ID propagated through async context (`AsyncLocalStorage`). Never `console.log` in production paths.
- **Metrics**: `prom-client` for RED per route — Rate (request count), Errors (error count), Duration (latency histogram). OpenTelemetry Node SDK for distributed traces across services.
- **Initialize tracing before app imports, then verify it fires**: the OTel SDK must start before the modules it instruments are required, or auto-instrumentation silently no-ops. Before relying on any signal, force an error and send test traffic in staging and confirm the log/metric/trace actually lands — untested instrumentation fails silent.
- **Alert on symptoms, not causes**: page on user-visible symptoms (error-rate spike, latency SLO burn, `/ready` flapping), not on causes (CPU high, heap growing). A cause with no symptom is a dashboard, not a page.
