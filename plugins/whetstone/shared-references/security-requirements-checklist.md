# Security Requirements Checklist

Load this reference as a final verification pass before emitting the audit report. Every item must be checked for the code under review.

- [ ] All inputs validated and sanitized at system boundaries
- [ ] No hardcoded secrets or credentials (env vars or secret manager only)
- [ ] Authorization per request, not just authentication
- [ ] SQL queries use parameterization or ORM query builders
- [ ] XSS protection implemented (proper output escaping)
- [ ] HTTPS enforced in production
- [ ] CSRF protection enabled for state-changing requests
- [ ] Security headers properly configured
- [ ] Rate limiting on authentication and public endpoints
- [ ] CORS restricted to specific allowed origins
- [ ] Passwords hashed with bcrypt/argon2 (never plaintext or reversible)
- [ ] Error messages don't leak stack traces or sensitive information
- [ ] Dependencies audited for known vulnerabilities

For stack-specific security tooling behind these generic requirements (Helmet in Node, Laravel middleware, FastAPI CORS), defer to the language skill (`ia-nodejs-backend`, `ia-php-laravel`, `ia-python-services`).
