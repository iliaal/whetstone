# API boundaries

## Framework Selection

| Context | Choose | Why |
|---------|--------|-----|
| Edge/Serverless | Hono | Zero-dep, fastest cold starts |
| Performance API | Fastify | Higher throughput than Express, built-in schema validation |
| Enterprise/team | NestJS | DI, decorators, structured conventions |
| Legacy/ecosystem | Express | Most middleware, widest adoption |

Ask user: deployment target, cold start needs, team experience, existing codebase.


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
