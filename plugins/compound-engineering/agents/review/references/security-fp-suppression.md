# Security False-Positive Suppression

Load this reference when running a security audit — before filing any finding, filter against these rules. Goal: a report a senior security engineer would confidently raise in a PR review, not a wall of "consider adding validation here."

## Hard exclusions (skip regardless of detection)

- **Denial of service / rate limiting / resource leaks** — unless the diff introduces explicit user-triggerable allocation of unbounded state. Generic "this could be a DoS vector" findings are noise.
- **Memory safety in managed languages** — no memory-safety findings on `.ts/.tsx/.js/.py/.php/.rb/.go` files. Only report on `.c/.cc/.cpp/.h/.rs` (and only in `unsafe` blocks for Rust).
- **SSRF in client-rendered HTML** — `.html/.jsx/.tsx/.vue` client code does not make server-side requests. Skip.
- **Regex injection / ReDoS** — only report when the regex is user-controlled AND runs server-side in a request-handling hot path. Static regexes compiled from developer input are not findings.
- **Markdown files** — documentation is not code; no findings.
- **React/Vue XSS without `dangerouslySetInnerHTML` / `v-html` / `innerHTML`** — frameworks escape by default. Flag only when the dangerous method is present.

## Precedents (not findings)

- User-provided content placed in the user-message position of an LLM prompt is NOT prompt injection. Flag only when user content enters system prompts, tool schemas, or function definitions.
- Logging non-PII request metadata (method, path, status) is not a vulnerability.
- Command-injection risk in project-internal shell scripts is a finding only when the script accepts untrusted external input. Internal-ops scripts run by developers are not in scope.
- "Consider adding validation" without a concrete failure mode is not a finding. Name the specific input, the specific sink, and the specific exploit.

## Confidence floor

Assign a confidence score (0.0-1.0) per finding. Report only at ≥ 0.8. Below 0.7 is suppressed entirely. At 0.7-0.8 the finding is recorded in "Residual Risks" rather than the main findings list.

This floor is deliberately stricter than `ia-code-review`'s general rubric (report at ≥ 0.6, critical security at ≥ 0.5). A dedicated security audit trades recall for precision — borderline findings belong in Residual Risks so reviewers aren't drowned in maybes. If a 0.7-0.8 finding does matter, it's still visible, just not in the main list.

## Severity gates

- **Medium findings** must be obvious and concrete (specific input, specific sink, specific harm). "Consider adding validation" without a failure mode belongs in advisory notes, not Medium findings.
- **Local-network-only exploitability does NOT auto-downgrade severity.** An auth bypass exploitable only from the internal network is still HIGH — internal services carry real blast radius, and lateral movement is cheap.

## Project-level overrides

If the project's `CLAUDE.md`, `AGENTS.md`, or a `.claude/project-security.md` file documents explicit overrides (e.g., "we intentionally expose X because Y", "internal tool, auth not enforced"), honor them. Do not re-raise the documented issue; do not fight the convention. If the override lacks rationale, suggest documenting it.
