# Security False-Positive Suppression

Load this reference when running a security audit — before filing any finding, filter against these rules. Goal: a report a senior security engineer would confidently raise in a PR review, not a wall of "consider adding validation here."

## Hard exclusions (skip regardless of detection)

- **Denial of service / rate limiting / resource leaks** — require a reachable hostile input and concrete resource or cost impact within actual limits: CPU exhaustion, unbounded allocation, blocking work, or paid-model/agent-loop exhaustion. Generic "this could be a DoS vector" without those conditions is noise; a CPU-bound fixed-regex exploit is not excluded merely because it allocates no unbounded state.
- **Memory safety in managed languages** — no memory-safety findings on `.ts/.tsx/.js/.py/.php/.rb/.go` files. Only report on `.c/.cc/.cpp/.h/.rs` (and only in `unsafe` blocks for Rust).
- **SSRF in client-rendered HTML** — `.html/.jsx/.tsx/.vue` client code does not make server-side requests. Skip.
- **Regex injection / ReDoS** — require a reachable attacker-controlled pattern or input and evidence of excessive work within the application's input limits. A fixed developer-written regex can catastrophically backtrack on hostile input; pattern ownership is not a defense. Bound reproduction time and report the input size and measured cost.
- **Markdown files** — distinguish passive prose from instructions consumed by agents, executable snippets, configuration, and exposed secrets. Review the behavior the content actually drives; a file extension does not establish a trust boundary.
- **React/Vue XSS without `dangerouslySetInnerHTML` / `v-html` / `innerHTML`** — frameworks escape by default. Flag only when the dangerous method is present.

## Precedents (not findings)

- A user's ordinary request is not prompt injection merely because it reaches an LLM. Trace whether lower-trust content can redirect the agent beyond the requesting user's authority or the application's intended task. Message role alone does not prove isolation: retrieved text inside a user message can still influence privileged tools. Require a concrete source, trust-boundary crossing, and unauthorized effect.
- Logging non-PII request metadata (method, path, status) is not a vulnerability.
- Command-injection risk in project-internal shell scripts is a finding only when the script accepts untrusted external input. Internal-ops scripts run by developers are not in scope.
- "Consider adding validation" without a concrete failure mode is not a finding. Name the specific input, the specific sink, and the specific exploit.
- **SSRF requires control of the host or scheme, not just the path.** Appending to a fixed base URL's path is not SSRF; flag it only when the attacker controls the destination host or protocol.
- **Environment variables and CLI flags are trusted inputs.** An "attack" that presumes the attacker already sets an env var or command-line flag is invalid in a secure deployment. Exception: env vars derived from untrusted sources (CGI `HTTP_*` headers, the httpoxy `Proxy` header, an uploaded `.env`) are attacker-controlled and in scope.
- **v4 UUIDs may be assumed unguessable.** A v4 UUID used as an identifier does not require an added unguessability control; "the UUID could be brute-forced" is not a finding. (v1 embeds a timestamp/MAC and v3/v5 are deterministic hashes — those are not unguessable.)
- **Theoretical races are not findings.** Report a race only with a concrete interleaving and an observable corruption or impact — not "this could race under load." (Counterweight to race *hunting*: hunt for TOCTOU, but file only a demonstrated one.)
- **Log spoofing / forging** (unsanitized user input written to logs) is not, by itself, a vulnerability.
- **Capability gain is the bar for a true positive.** Show what exploitation grants beyond the attacker's existing authority — data, privilege, execution, persistence, or a concrete availability/cost impact. Deployment preconditions and internal reach affect feasibility and severity; neither automatically refutes a finding nor fixes its tier. Use the impact and reachability evidence in `ia-code-review`'s severity rubric.

## Confidence floor

State confidence from the evidence: reproduced, supported by a traced path, or unresolved. Numeric scores, when the caller requires them, are uncalibrated judgment labels, not probabilities. Main findings need a concrete failure path and supporting evidence; consequential unresolved candidates belong in Residual Risks with the missing check. Neither a high score nor reviewer agreement substitutes for proof.

## Severity gates

- **Medium findings** must be obvious and concrete (specific input, specific sink, specific harm). "Consider adding validation" without a failure mode belongs in advisory notes, not Medium findings.
- **Local-network-only exploitability does not determine severity.** Assess the required foothold, controls, capability gain, and blast radius. An internal auth bypass can still be severe; an internal-only label alone justifies neither a downgrade nor HIGH.

## Project-level overrides

If the project's `CLAUDE.md`, `AGENTS.md`, a threat model or ADR, or a `.claude/project-security.md` file documents explicit overrides (e.g., "we intentionally expose X because Y", "internal tool, auth not enforced", a component marked out of scope with a reason), honor them during ordinary diff review. Do not re-raise the documented issue; do not fight the convention. If the override lacks rationale, suggest documenting it.

The honoring is venue-scoped. A full-repository audit is where the rationale itself gets re-derived: test the stated reason against current source before accepting it, per the documented-exclusions rule in [security-adversarial-pass.md](./security-adversarial-pass.md) — a dated exclusion is a claim, not proof, and the code it described may have changed since.
