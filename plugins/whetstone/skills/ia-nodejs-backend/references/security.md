# Authentication & Security

For comprehensive security auditing (OWASP compliance, vulnerability scanning, checklist), use the `ia-security-sentinel` agent. This reference covers Node.js-specific tooling and patterns only.

## Authentication Pattern

- **Access token**: JWT, 15min expiry, payload: `{ userId, email }`
- **Refresh token**: JWT, 7d expiry, stored in DB (revocable)
- **Passwords**: bcrypt (10+ rounds) or argon2
- **Middleware**: extract `Bearer` token → `jwt.verify` → attach `req.user` → `next()`
- **Authorization**: after auth, check role or resource ownership per request
- Always return generic "Invalid credentials" -- never reveal if user exists

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

`npm audit` catches *known advisories only* — not a freshly-malicious or typosquatted package. Harden the install itself:

- **Frozen installs.** Commit the lockfile and install with the manager's immutable mode (`npm ci`, `pnpm install --frozen-lockfile`, `yarn install --immutable`) so CI can't silently resolve a different tree.
- **Gate lifecycle scripts.** Block dependency `preinstall`/`postinstall` scripts by default and approve them per-package via the manager's native policy, so a compromised transitive dependency can't run arbitrary code at install time. The exact flag is manager- and version-specific — resolve it via Context7 rather than hardcoding it.
- **Audit ≠ safety.** A clean `npm audit` is not proof a dependency is trustworthy. Never run `npm audit fix --force` unattended — it can jump majors and break the build. Treat audit as one signal, not a gate.
- **Verify provenance** where the registry supports it (npm signature/provenance attestations) before adding a new or unfamiliar package.
