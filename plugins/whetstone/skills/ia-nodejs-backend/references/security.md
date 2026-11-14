# Authentication & Security

For full security auditing (OWASP compliance, vulnerability scanning, checklist), use the `ia-security-sentinel` agent when installed. Otherwise use `ia-code-review` with a security focus. This reference covers Node.js-specific tooling and patterns only.

## Authentication Pattern

- **Access token**: JWT, 15min expiry, payload: `{ userId, email }`
- **Refresh token**: JWT, 7d expiry, stored in DB (revocable)
- **Passwords**: bcrypt (10+ rounds) or argon2
- **Middleware**: extract `Bearer` token → `jwt.verify` → attach `req.user` → `next()`
- **NestJS: before v12.2.0, scoped middleware and global enhancers can silently not run.** Through v12.1.3, route-middleware registration skips a `Scope.TRANSIENT` middleware with no error or warning; before v12.1.0 the skip also dropped every middleware listed after it in `consumer.apply(...)`, so an `AuthMiddleware` placed after a transient logger left the routes unauthenticated. Enforce authn/authz in a guard. Later releases through v12.5.0 closed further gaps; each item below names the versions it affects:
  - Never register a global guard, pipe, interceptor, or filter as `Scope.TRANSIENT`. Transient global enhancers are skipped on HTTP and microservice controllers through v12.1.2, and on GraphQL resolvers through v12.1.3.
  - A default-scoped global enhancer whose dependency tree contains a request-scoped provider is not safe as a singleton. Through v12.1.2 it ran with `undefined` dependencies (`useClass`) or never ran (`useExisting`, `useFactory`); v12.1.3 fails at startup instead. Mark it `@Injectable({ scope: Scope.REQUEST })` explicitly and register it with `useClass`.
  - Through v12.1.3, a gateway or resolver guard that becomes request-scoped through its dependencies can be read from a context where its constructor never ran.
  - NestJS v12.3.3 only: `forRoutes()` drops a plain-string path when a parameterized `RequestMethod.ALL` route in the same call matches it, so the middleware stops running on that path's subpaths. Upgrade to v12.4.0, or e2e-test a subpath of every plain-string middleware route.
  - Before v12.5.0, route-bound middleware also skips requests its route still serves: percent-encoded reserved characters in a segment that mixes a parameter and text on Fastify or the Node adapter, non-ASCII case folds on case-insensitive Fastify, routes on the other side of a global-prefix exclusion, and a non-`@Controller()` base class passed to `forRoutes()` (mounted nowhere; v12.5.0 fails startup). Before v12.4.1, `forRoutes('*')` also skips prefix-excluded routes at a non-default URI version. Keep any check that must run on every request (auth, tenant scoping, CSRF) in a guard or a global hook.
  - Before v12.5.0, a guard, interceptor, or pipe that resolves to an object without `canActivate`, `intercept`, or `transform` is dropped without error and the route runs unguarded: an abstract class used as the DI token in `@UseGuards()`, a mixin guard factory passed uncalled (`@UseGuards(RoleGuard)` instead of `RoleGuard('admin')`), an `APP_GUARD` whose `useValue` or `useFactory` yields a class or promise, or a class passed to `app.useGlobalGuards()`. These shapes type-check, because `@UseGuards()` accepts any `Function`. v12.5.0 fails startup instead. A filter class passed to `app.useGlobalFilters()` or as an `APP_FILTER` `useValue` is skipped on every version (v12.5.0 only warns); pass filter instances. Keep one denied-request e2e test per distinct guard binding, not one per app.

  On every version, a request- or transient-scoped `APP_FILTER` does not handle exceptions from middleware, unknown routes, or body parsing; v12.2.0 only logs a warning. Register an unscoped global filter alongside it, or the internal error details it was meant to hide leak on those paths. Keep a denied-call e2e test on every transport the app exposes (HTTP, GraphQL, WebSocket, microservice): one unauthenticated HTTP 401 test does not cover the others. Before NestJS v12.5.0, gateways sharing a port and path use only the first-declared gateway's `verifyClient` (ws) or `allowRequest` (Socket.IO), so a later gateway's handshake check never runs; v12.5.0 fails startup on mismatched checks. On older versions, put the check on every gateway of a shared server or in a `@SubscribeMessage` guard, and include a rejected-handshake test per gateway.
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

Before NestJS v12.5.0, a route's `FileInterceptor` option set to `undefined` or `null` (an unset config value) replaces the `MulterModule` value by object spread, so a limit, the whole `limits` object, the storage, or the `fileFilter` disappears; a `fileFilter` that throws or rejects crashes Express and Node adapter apps instead of failing the request; and an upload that an earlier interceptor (such as a timeout) already answered keeps being received and stored. On those versions, drop nullish keys before passing route options, and wrap filter bodies in `try`/`catch` that calls back with the error. v12.5.0 ignores nullish route options, so `undefined` no longer lifts a module limit; use `Infinity` to lift one.

## Dependency Supply Chain

`npm audit` catches *known advisories only*, not a freshly-malicious or typosquatted package. Harden the install itself:

- **Frozen installs.** Commit the lockfile and install with the manager's immutable mode (`npm ci`, `pnpm install --frozen-lockfile`, `yarn install --immutable`) so CI can't silently resolve a different tree.
- **Gate lifecycle scripts.** Block dependency `preinstall`/`postinstall` scripts by default and approve them per-package via the manager's native policy, so a compromised transitive dependency can't run arbitrary code at install time. Verify the exact manager- and version-specific flag in current official documentation. Prefer Context7 when available; otherwise read the package manager's official docs with available web tools.
- **Release-age floor.** Configure the manager to refuse versions published more recently than a cooldown window set by team policy, in days (pnpm `minimumReleaseAge` in minutes, npm `min-release-age` in days), so a freshly published malicious version is not installed on the next update. When a newer version is approved, exempt only that exact `package@version` (pnpm `minimumReleaseAgeExclude` accepts `name@version`; npm `min-release-age-exclude` matches package names or globs, so it exempts every version of the package), keep inherited exclusions, and never lower or disable the floor globally. Accept the exception only after the ordinary frozen install exits 0 without temporary overrides; an update command, printed config, or regenerated lockfile does not prove it.
- **Audit ≠ safety.** A clean `npm audit` is not proof a dependency is trustworthy. Never run `npm audit fix --force` unattended; it can jump majors and break the build. Treat audit as one signal, not a gate.
- **Verify provenance** where the registry supports it (npm signature/provenance attestations) before adding a new or unfamiliar package.

## Secrets resolved by running a command

A config option that fetches a secret by shelling out (`api_key_cmd`, git's `credential.helper`, AWS's `credential_process`, a `1password`/`gpg`/`vault` wrapper) is a subprocess whose failure modes are not the usual ones:

- **A timeout on the child is not a timeout on the pipe.** Killing or cancelling the immediate child leaves a grandchild it spawned (`gpg-agent`, `pinentry`, a browser prompt) holding the inherited stdout descriptor, so the read never returns and the request hangs past its deadline. Set a hard timeout, then a short grace period after it, then force-close the output pipe rather than waiting on the reader. In Node this is `child_process.spawn` with `timeout` plus an explicit `killSignal`, followed by destroying `stdout`; the `timeout` option alone only signals the child.
- **Cap the output buffer explicitly when using `spawn`.** An unbounded read of a credential helper's stdout means a misbehaving or wrong-binary command (a helper that prints a log, or a path that resolves to something that streams) grows the parent's heap until it dies. `spawn` has **no** `maxBuffer` option; passing one is silently ignored, so count bytes in the `data` handler and kill the child and destroy the stream past the cap, reusing the `killSignal` from the timeout path above. `execFile` does honor `maxBuffer`, but it truncates the captured buffer to the cap and *then* reports `ERR_CHILD_PROCESS_STDIO_MAXBUFFER`, so a caller that ignores the error reads a silently shortened secret.

Validate the resolved value for control bytes before it is used, per the CRLF/header-injection rows in `ia-code-review`'s security-patterns reference; a credential provider is an unusually direct path from external state into an `Authorization` header.
