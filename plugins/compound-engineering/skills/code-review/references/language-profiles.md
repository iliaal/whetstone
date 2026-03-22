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

- Secrets in plaintext (API keys, passwords, tokens)
- Missing timeouts, retries, or pool limits on service connections
- Overly permissive CORS or security headers
- Default/development values left in production configs

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
