# Security Test Coverage Checklist

Audit checklist for the `ia-security-sentinel` report. Classify each item as verified (cite source and actual test evidence), uncovered (name the missing check), or not applicable (explain why). A checklist may be inline; create a separate artifact only when the caller requests or needs one.

Demonstrated vulnerabilities carry CVSS 3.1 base score/vector, exploit evidence, and a verified remediation or a concrete remedy explicitly awaiting validation. Missing tests are coverage gaps, not evidence of exploitability.

## Authentication edge cases

- [ ] Missing token → 401, not 500
- [ ] Expired token → refresh or re-auth path exercised
- [ ] Token with `alg=none` or weak algorithm → rejected
- [ ] Wrong issuer / audience / key ID → rejected
- [ ] Token reuse after logout → rejected

## Authorization

- [ ] Per-request authorization, not just authentication
- [ ] IDOR: direct object reference with another user's ID → denied
- [ ] Vertical privilege escalation: regular user hitting admin routes → denied
- [ ] Horizontal: user A editing user B's resource → denied

## Input boundary

- [ ] Mass assignment: extra fields in request body → stripped or rejected
- [ ] Type confusion: array where string expected, negative where positive expected
- [ ] File upload: magic-byte validation, executable rejection, size limits, filename sanitization (no `..`, no null bytes)
- [ ] Business logic: negative quantities, zero-price orders, workflow step bypass

## Concurrency and state

- [ ] Race conditions (TOCTOU): check-then-act patterns → atomic replacement
- [ ] Double-submit / replay → idempotency key or nonce
- [ ] Partial-completion rollback on crash mid-operation

## Session and cookie hygiene

- [ ] `HttpOnly`, `Secure`, `SameSite=Lax` (or `Strict`) on all session cookies
- [ ] Session fixation: session ID rotated on login
- [ ] Session invalidation on logout server-side, not just client

## Output boundary

- [ ] XSS: user content in HTML context, attribute context, JS context, URL context → all escaped
- [ ] `dangerouslySetInnerHTML` / `v-html` / `innerHTML` with user data → flagged
- [ ] Error messages don't leak stack traces, query fragments, or internal paths

## Per-finding output format

For each finding, emit:

1. **ID**: `SS-001`, `SS-002`... sequential across all severities
2. **Severity**: CVSS 3.1 base score + vector string
3. **Proof**: curl command, test snippet, or exploit PoC that demonstrates the vulnerability
4. **Remediation**: a verified code fix, or a concrete proposed remedy labeled unvalidated with the command or test needed to validate it

Report uncovered items under Coverage gaps / Residual Risks, separate from demonstrated vulnerabilities. Do not assign a CVSS score or fabricate exploit proof for the absence of a test.
