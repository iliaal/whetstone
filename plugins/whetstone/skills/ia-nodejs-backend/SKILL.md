---
name: ia-nodejs-backend
class: language
description: >-
  Node.js backend patterns: layered architecture, TypeScript, validation, error
  handling, security, observability, logging, metrics, deployment. Use when building REST APIs, REST endpoints, middleware,
  Express/Fastify/Hono/NestJS/Koa servers, tRPC procedures, Bun servers, or server-side TypeScript.
paths: "**/*.ts,**/*.js,**/*.mjs,**/*.cjs"
---

# Node.js Backend

**Verify before implementing**: For framework-specific APIs (Express 5, Fastify 5, Node.js 22+ built-ins), look up current docs via Context7 (`query-docs`) before writing code. Training data may lag current releases.

## Framework Selection

| Context | Choose | Why |
|---------|--------|-----|
| Edge/Serverless | Hono | Zero-dep, fastest cold starts |
| Performance API | Fastify | Higher throughput than Express, built-in schema validation |
| Enterprise/team | NestJS | DI, decorators, structured conventions |
| Legacy/ecosystem | Express | Most middleware, widest adoption |

Ask user: deployment target, cold start needs, team experience, existing codebase.

## Architecture

```
src/
├── routes/          # HTTP: parse request, call service, format response
├── middleware/       # Auth, validation, rate limiting, logging
├── services/        # Business logic (no HTTP types)
├── repositories/    # Data access only (queries, ORM)
├── config/          # Env, DB pool, constants
└── types/           # Shared TypeScript interfaces
```

- Routes never contain business logic
- Services never import Request/Response
- Repositories never throw HTTP errors
- Dependencies point inward only (Clean Architecture rule): routes -> services -> repositories. Never the reverse.
- For scripts/prototypes: single file is fine -- ask "will this grow?"

## TypeScript Rules

- Use `import type { }` for type-only imports -- eliminates runtime overhead
- Prefer `interface` for object shapes (2-5x faster type resolution than intersections)
- Prefer `unknown` over `any` -- forces explicit narrowing
- Use `z.infer<typeof Schema>` as single source of truth -- never duplicate types and schemas
- Minimize `as` assertions -- use type guards instead
- Add explicit return types to exported functions (faster declaration emit)
- Untyped package? `declare module 'pkg' { const v: unknown; export default v; }` in `types/ambient.d.ts`

## Validation

**Zod** (TypeScript inference) or **TypeBox** (Fastify native). Validate at boundaries only: request entry, before DB ops, env vars at startup. Use `.extend()`, `.pick()`, `.omit()`, `.partial()`, `.merge()` for DRY schemas.

- **`z.coerce.boolean()` is `Boolean(v)`.** Every non-empty string is truthy, so the literal strings `"false"`, `"0"`, `"no"` and `"off"` all coerce to `true`; only `""` and a real boolean `false` yield `false`. Clients and LLM callers routinely emit booleans as JSON strings, and the advertised schema saying `type: boolean` does not stop a host that forwards arguments unvalidated. The damage concentrates exactly where it is worst: a default-true flag can be forced on but never string-off, and a destructive flag (`kill_existing`, `force`, `active`) passed `"false"` fires. Use plain `z.boolean()` where fail-loud is acceptable, or `z.preprocess` the known spellings before `z.boolean()` so unrecognized strings still reject rather than silently becoming `true`. `.optional()` short-circuits `undefined` before the preprocess, so optional params still default correctly, and JSON Schema generation still emits `{ type: "boolean" }`.
- **Zod v4 removed the single-argument `z.record(valueType)`** -- it requires `z.record(keyType, valueType)`, e.g. `z.record(z.string(), z.number())`. TypeScript rejects the single-arg form immediately (`tsc`: `Expected 2-3 arguments, but got 1`). If the type error is suppressed, the lone argument becomes the KEY schema and `valueType` stays `undefined`, so the first `.parse()` on a non-empty object throws `TypeError: Cannot read properties of undefined (reading '_zod')` — a raw TypeError, not a Zod validation error.

## Error Handling

Custom error hierarchy: `AppError(message, statusCode, isOperational)` → `ValidationError(400)`, `NotFoundError(404)`, `UnauthorizedError(401)`, `ForbiddenError(403)`, `ConflictError(409)`

Centralized handler middleware:
- `AppError` → return `{ error: message }` with statusCode
- Unknown → log full stack, return 500 + generic message in production
- Async wrapper: `const asyncHandler = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);`

Codes: 400 bad input | 401 no auth | 403 no permission | 404 missing | 409 conflict | 422 business rule | 429 rate limited | 500 server fault

## API Design

**Contract-first**: define route schemas (Zod schemas, Fastify JSON Schema, or OpenAPI spec) before writing handler logic. The schema is the contract -- implementation follows. Generate OpenAPI/Swagger docs from these schemas for interactive API documentation.

- **Hyrum's Law awareness**: every observable response field, ordering, or timing becomes a dependency for callers. Use Zod schemas or Fastify response schemas to control exactly what's serialized -- never return raw ORM objects or untyped objects from handlers.
- **Addition over modification**: add new optional fields rather than changing or removing existing ones. Removing a field from a response schema breaks callers silently. Deprecate first (mark in OpenAPI spec), remove in a later version.
- **Consistent error envelope**: all errors -- validation, auth, not-found, application -- must produce the same `{ error: { code, message, details? } }` structure. Centralize in the error handler middleware. Callers build error handling once; inconsistent errors force per-endpoint special cases.
- **Boundary validation**: validate at the middleware/route handler level (Zod `.parse()` on request body/params, Fastify schema validation). Services and repositories trust that input was validated at entry -- no redundant checks scattered through business logic.
- **Third-party responses are untrusted data**: validate shape and content of external API responses before using them in logic, rendering, or decision-making. A compromised or misbehaving service can return unexpected types, malicious content, or missing fields. Parse through a Zod schema before use.
- **Resources**: plural nouns (`/users`), max 2 nesting levels (`/users/:id/orders`)
- **Methods**: GET read | POST create | PUT replace | PATCH partial | DELETE remove
- **Versioning**: URL path `/api/v1/`
- **Response**: `{ data, pagination?: { page, limit, total, totalPages } }`
- **Queries**: `?page=1&limit=20&status=active&sort=createdAt,desc`
- Return `Location` header on 201. Use 204 for successful DELETE with no body.

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

## Observability

- **Define "working" before instrumenting**: write the questions an on-call engineer will ask when this is broken at 3am ("which dependency is timing out?", "is it all users or one tenant?"), then add only the telemetry that answers them. Instrumentation with no question behind it is cost and noise.
- **Pick the signal by the question it answers**: logs = "what happened in this one case?" (high-detail, structured, sampled under load); metrics = "how often / how fast / how saturated?" (cheap aggregates — keep label cardinality bounded, never user IDs or request IDs as labels); traces = "where did the time or the error go across services?".
- **Structured logging**: `pino` with a stable set of event names and a correlation/request ID propagated through async context (`AsyncLocalStorage`). Never `console.log` in production paths.
- **Metrics**: `prom-client` for RED per route — Rate (request count), Errors (error count), Duration (latency histogram). OpenTelemetry Node SDK for distributed traces across services.
- **Initialize tracing before app imports, then verify it fires**: the OTel SDK must start before the modules it instruments are required, or auto-instrumentation silently no-ops. Before relying on any signal, force an error and send test traffic in staging and confirm the log/metric/trace actually lands — untested instrumentation fails silent.
- **Alert on symptoms, not causes**: page on user-visible symptoms (error-rate spike, latency SLO burn, `/ready` flapping), not on causes (CPU high, heap growing). A cause with no symptom is a dashboard, not a page.

## Discipline

- Simplicity first -- every change as simple as possible, impact minimal code
- Only touch what's necessary -- avoid introducing unrelated changes
- No hacky workarounds -- if a fix feels wrong, step back and implement the clean solution
- Before adding a new abstraction, verify it appears in 3+ places. If not, inline it.
- If a fix requires bypassing TypeScript (`as any`, non-null assertions on untrusted data, `// @ts-ignore`), treat it as a design smell and find the typed solution

## Verify

- `tsc --noEmit` passes with zero errors
- `npm test` passes with zero failures
- No TypeScript bypasses (`as any`, `@ts-ignore`) in new code

## References

- [TypeScript config](./references/typescript-config.md) -- tsconfig, ESM, branded types, compiler performance
- [Security](./references/security.md) -- JWT, password hashing, rate limiting, OWASP
- [API design patterns](./references/api-design.md) -- pagination, filtering, sorting, deprecation, idempotency-key claim and retention
- [Database & production](./references/database-production.md) -- connection pooling, transactions, Docker, logging
