# Authentication & Security

For full security auditing (OWASP compliance, vulnerability scanning, checklist), use the `ia-security-sentinel` agent when installed. Otherwise use `ia-code-review` with a security focus. This reference covers Node.js-specific tooling and patterns only.

## Authentication Pattern

- **Access token**: JWT, 15min expiry, payload: `{ userId, email }`
- **Refresh token**: JWT, 7d expiry, stored in DB (revocable)
- **Passwords**: bcrypt (10+ rounds) or argon2
- **Middleware**: extract `Bearer` token → `jwt.verify` → attach `req.user` → `next()`
- **NestJS: before v12.2.0, scoped middleware and global enhancers can silently not run.** Through v12.1.3, route-middleware registration skips a `Scope.TRANSIENT` middleware with no error or warning; before v12.1.0 the skip also dropped every middleware listed after it in `consumer.apply(...)`, so an `AuthMiddleware` placed after a transient logger left the routes unauthenticated. Enforce authn/authz in a guard. On older versions:
  - Never register a global guard, pipe, interceptor, or filter as `Scope.TRANSIENT`. Transient global enhancers are skipped on HTTP and microservice controllers through v12.1.2, and on GraphQL resolvers through v12.1.3.
  - A default-scoped global enhancer whose dependency tree contains a request-scoped provider is not safe as a singleton. Through v12.1.2 it ran with `undefined` dependencies (`useClass`) or never ran (`useExisting`, `useFactory`); v12.1.3 fails at startup instead. Mark it `@Injectable({ scope: Scope.REQUEST })` explicitly and register it with `useClass`.
  - Through v12.1.3, a gateway or resolver guard that becomes request-scoped through its dependencies can be read from a context where its constructor never ran.

  On every version, a request- or transient-scoped `APP_FILTER` does not handle exceptions from middleware, unknown routes, or body parsing; v12.2.0 only logs a warning. Register an unscoped global filter alongside it, or the internal error details it was meant to hide leak on those paths. Keep a denied-call e2e test on every transport the app exposes (HTTP, GraphQL, WebSocket, microservice): one unauthenticated HTTP 401 test does not cover the others.
- **Authorization**: after auth, check role or resource ownership per request
- Always return generic "Invalid credentials"; never reveal if user exists

## Node.js Security Tooling

| Concern | Tool/Package | Usage |
|---------|-------------|-------|
| Input validation | Zod / TypeBox | Validate at route boundary |
| Security headers | Helmet | `app.use(helmet())` |
| Rate limiting | express-rate-limit + Redis store | Stricter on auth endpoints |
| CORS | cors package | Restrict to specific origins |
| Dependency audit | `npm audit` | Run regularly in CI (see Dependency Supply Chain for caveats) |
| Secrets | env vars via dotenv/vault | Validate at startup, never commit |

## Dependency Supply Chain

`npm audit` catches *known advisories only*, not a freshly-malicious or typosquatted package. Harden the install itself:

- **Frozen installs.** Commit the lockfile and install with the manager's immutable mode (`npm ci`, `pnpm install --frozen-lockfile`, `yarn install --immutable`) so CI can't silently resolve a different tree.
- **Gate lifecycle scripts.** Block dependency `preinstall`/`postinstall` scripts by default and approve them per-package via the manager's native policy, so a compromised transitive dependency can't run arbitrary code at install time. Verify the exact manager- and version-specific flag in current official documentation. Prefer Context7 when available; otherwise read the package manager's official docs with available web tools.
- **Audit ≠ safety.** A clean `npm audit` is not proof a dependency is trustworthy. Never run `npm audit fix --force` unattended; it can jump majors and break the build. Treat audit as one signal, not a gate.
- **Verify provenance** where the registry supports it (npm signature/provenance attestations) before adding a new or unfamiliar package.

## Secrets resolved by running a command

A config option that fetches a secret by shelling out (`api_key_cmd`, git's `credential.helper`, AWS's `credential_process`, a `1password`/`gpg`/`vault` wrapper) is a subprocess whose failure modes are not the usual ones:

- **A timeout on the child is not a timeout on the pipe.** Killing or cancelling the immediate child leaves a grandchild it spawned (`gpg-agent`, `pinentry`, a browser prompt) holding the inherited stdout descriptor, so the read never returns and the request hangs past its deadline. Set a hard timeout, then a short grace period after it, then force-close the output pipe rather than waiting on the reader. In Node this is `child_process.spawn` with `timeout` plus an explicit `killSignal`, followed by destroying `stdout`; the `timeout` option alone only signals the child.
- **Cap the output buffer explicitly when using `spawn`.** An unbounded read of a credential helper's stdout means a misbehaving or wrong-binary command (a helper that prints a log, or a path that resolves to something that streams) grows the parent's heap until it dies. `spawn` has **no** `maxBuffer` option; passing one is silently ignored, so count bytes in the `data` handler and kill the child and destroy the stream past the cap, reusing the `killSignal` from the timeout path above. `execFile` does honor `maxBuffer`, but it truncates the captured buffer to the cap and *then* reports `ERR_CHILD_PROCESS_STDIO_MAXBUFFER`, so a caller that ignores the error reads a silently shortened secret.

Validate the resolved value for control bytes before it is used, per the CRLF/header-injection rows in `ia-code-review`'s security-patterns reference; a credential provider is an unusually direct path from external state into an `Authorization` header.
