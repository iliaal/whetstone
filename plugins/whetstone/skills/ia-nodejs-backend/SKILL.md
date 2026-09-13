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

## Working rules

- Validate request and third-party data before use; keep response serialization and error envelopes explicit.
- Preserve caller-visible contracts and authorization when adding resilience or fallbacks.
- Bound concurrency, set timeouts, and avoid blocking production request paths.
- Verify actual resource identity before parsing or caching a reused client's result.
- Exercise operational telemetry and failure paths, not successful return codes alone.

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

## Task-specific references

Read the relevant reference before implementing or reviewing the matching behavior:

- For framework choice, input validation, API contracts, or errors: [api-boundaries.md](./references/api-boundaries.md).
- For concurrency, networking, startup, caches, lifecycle cleanup, or telemetry: [async-and-production.md](./references/async-and-production.md).
- For span kinds, HTTP-status-to-span-status rules, sampling placement, metric cardinality, or telemetry data governance: [observability-tracing.md](./references/observability-tracing.md).

Existing specialized references, when the corresponding topic applies:
