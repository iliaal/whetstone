# Security Test Coverage Checklist

Audit deliverable template for the `security-sentinel` agent. Every security audit must produce this checklist as an explicit artifact, not a narrative summary. Each item is either verified with evidence (file:line + passing test) or explicitly flagged as uncovered.

Each finding ties to severity (CVSS 3.1 base score + vector), proof of exploitability (curl command, test snippet, or PoC), and copy-paste-ready remediation code.

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
4. **Remediation**: copy-paste-ready code fix, not just a description

Uncovered checklist items are explicit findings too — mark them `UNCOVERED: no test exists for <item>` so the user sees both failures AND gaps.
