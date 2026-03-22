# Authentication & Security

For comprehensive security auditing (OWASP compliance, vulnerability scanning, checklist), use the `security-sentinel` agent. This reference covers Node.js-specific tooling and patterns only.

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
| Dependency audit | `npm audit` | Run regularly in CI |
| Secrets | env vars via dotenv/vault | Validate at startup, never commit |
