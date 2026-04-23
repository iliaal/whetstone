# Adversarial Pass

Load this reference after completing the Phase 0-2 scans. Purpose: find what the checklist-driven review missed.

## Happy-path assumptions

Identify code paths that only work correctly when inputs are well-formed. What happens when a JSON body contains unexpected types, arrays where strings are expected, or negative numbers where only positive are valid? Look for implicit assumptions that break under adversarial input.

## Silent failures

Find places where errors are caught and swallowed without logging or re-raising. These are blind spots — an attacker can trigger failures repeatedly and the team will never know. Every caught exception in an auth, payment, or data-access path should produce an observable signal.

## Trust boundary violations

Trace user input through the full request lifecycle. Does user-supplied data flow into privileged operations (admin queries, internal API calls, file system access, queue payloads) without re-validation at the boundary? Validation at the HTTP layer doesn't protect internal services that accept the same data from a queue or RPC call.

## Cross-category compound vulnerabilities

Look for issues that span multiple security domains simultaneously. A weak authorization check combined with a mass-assignment vulnerability becomes a privilege escalation. A permissive CORS policy combined with a CSRF gap becomes a full account takeover. Standard scans check categories in isolation — this pass looks for combinations.

## Attacker prioritization

For each finding, answer two questions:

1. What is the easiest path to exploit this? If it requires chaining three bugs, it's lower priority than a single unauthenticated endpoint that leaks PII.
2. What is the highest-impact vulnerability that a standard automated scan would miss? Prioritize findings by exploitability and blast radius, not by category.
