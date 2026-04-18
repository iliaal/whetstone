# Language-Specific Review Profiles

Load the relevant profile(s) based on file extensions present in the diff.

## TypeScript / React (.ts, .tsx, .jsx)

- Hook dependency bugs (stale closures in useEffect)
- `any` escape hatches -- flag each with a concrete type suggestion
- Unchecked nullable access (`?.` chains that silently swallow nulls)
- Missing `key` props in mapped JSX
- Effects without cleanup (subscriptions, timers, event listeners)

## Python (.py)

- Mutable default arguments (`def f(items=[])`)
- Bare `except:` -- always catch specific exceptions
- Missing `async`/`await` (sync call in async context)
- f-string injection in SQL/shell -- use parameterized queries
- `type: ignore` without justification

## PHP (.php)

- SQL injection via string concatenation -- use prepared statements
- Missing `declare(strict_types=1)` at file top
- Type coercion traps (loose `==` vs strict `===`)
- Mass assignment without `$fillable` guard
- Unvalidated request input passed to Eloquent

## Shell (.sh, .bash, CI configs)

- Unquoted variables (`$var` vs `"$var"`)
- Missing `set -euo pipefail`
- Command injection via unsanitized input in `eval` or backticks
- `cd` without error check -- use `cd dir || exit 1`
- Hardcoded paths that should be variables

## Configuration (.env, .yml, .yaml, .json, .toml)

Use numbered IDs (CFG-001 ... CFG-006) so config-specific findings can be referenced unambiguously when a review turns up several related config issues:

- **CFG-001 Plaintext secrets**: API keys, passwords, tokens, DB URIs committed in config files. Use secret managers or `.env` excluded from VCS.
- **CFG-002 Magnitude-change without baseline**: a config value shifts by >2x (rate limits, batch sizes, pool caps, retry counts) without a PR-body justification or pre-change baseline measurement. High-magnitude shifts need explicit reasoning.
- **CFG-003 Timeout / retry hierarchy inversion**: inner call has a longer timeout than outer, or retries compound across layers (client 3× on top of SDK 3× = 9 attempts). Either cascades into thundering-herd failures.
- **CFG-004 Pool / limit mismatch**: connection pool, worker count, or queue depth does not match the downstream capacity (DB max_connections, upstream rate limit, available memory). Starves under load or overwhelms the downstream.
- **CFG-005 Env drift**: development values (localhost, short timeouts, verbose logging, permissive CORS) copied to production config without proportional scaling.
- **CFG-006 Rollback / observability gap**: risky config change lacks a feature flag, canary rollout, or reversible plan; or lacks the metric/alert needed to detect a regression post-deploy.

## Data Formats (.csv, .json ingestion, parsers)

- Missing encoding declaration (UTF-8 BOM handling)
- No size/row limit on ingested files (memory exhaustion)
- Trusting field count/shape without validation

## Security (all files)

- Show attacker-controlled input path to vulnerable sink, not just "possible injection"
- Injection vectors: SQL, XSS, CSRF, SSRF, command, path traversal, unsafe deserialization
- Race conditions: TOCTOU, check-then-act

## LLM Trust Boundaries

- LLM-generated values (emails, URLs, names) written to DB or mailers without format validation
- Structured tool output accepted without type/shape checks
- 0-indexed lists in prompts (LLMs return 1-indexed)
- Prompt text listing capabilities that don't match what's wired up
