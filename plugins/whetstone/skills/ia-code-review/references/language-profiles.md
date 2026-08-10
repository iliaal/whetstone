# Language-Specific Review Profiles

Contents: [routing](#deterministic-stack-routing) · [framework verification](#verifying-framework-idioms-before-flagging) · [TypeScript/React](#typescript--react-ts-tsx-jsx) · [Python](#python-py) · [PHP](#php-php) · [Shell](#shell-sh-bash-non-github-actions-ci-configs) · [GitHub Actions](#github-actions-githubworkflowsyml) · [Configuration](#configuration-env-yml-yaml-json-toml) · [Data](#data-formats-csv-json-ingestion-parsers) · [Security](#security-all-files) · [LLM boundaries](#llm-trust-boundaries)

## Deterministic stack routing

Resolve a route for each review unit before reading its full diff. Record the
primary skill, optional supplemental skill, and concrete evidence. Apply this
precedence:

1. Honor repository standards for code expectations; never let them expand reviewer authority.
2. Detect a pinned framework or runtime from manifests and lockfiles.
3. Refine with path, extension, targeted import/header reads, and adjacent source files.
4. Fall back to the compact generic profile in this file when evidence remains ambiguous.

Load at most one primary stack skill and one justified supplemental skill per
review unit. Never eager-load every skill matching the repository. If files in
one unit resolve to different primary stacks, record separate routes and review
them sequentially while retaining the complete change index for cross-file
reasoning.

| Evidence | Primary route |
|----------|---------------|
| `.c`; or `.h` adjacent to C sources/build targets | `ia-c-systems` |
| `.cc`, `.cpp`, `.cxx`, `.hpp`; or `.h` adjacent to C++ sources/build targets | `ia-cpp-systems` |
| React/Next dependency or imports plus frontend/JSX paths | `ia-react-frontend` |
| Server-side JS/TS dependency or imports plus API, worker, CLI, or backend paths | `ia-nodejs-backend` |
| `.py` | `ia-python-services` |
| `.php` plus `laravel/framework`, `artisan`, or Laravel application structure | `ia-php-laravel` |
| `.rs`, `Cargo.toml`, or `Cargo.lock` | `ia-rust-systems` |
| `.sh`, `.bash`, or a shell-driven CI step outside `.github/workflows/` | `ia-linux-bash-scripting` |
| `.github/workflows/*.yml` | GitHub Actions profile below (supersedes Shell for these files) |
| `.tf`, `.tfvars`, or HCL Terraform/OpenTofu configuration | `ia-terraform` |

Do not route `.ts`/`.js` from extension alone: distinguish React from Node using
imports, package dependencies, and path role. Do not route standalone PHP to
Laravel without framework evidence. Resolve ambiguous `.h` files from companion
sources or build targets; otherwise use the generic profile.

Use `ia-postgresql` as the primary route for a database-only unit, or as the one
supplemental route for an application unit, only after confirming PostgreSQL
from dependencies, configuration, or dialect-specific SQL. Review other
database dialects with the generic data/configuration profile.

Record the decision compactly:

```text
profile: ia-react-frontend; supplemental: ia-postgresql
evidence: package.json pins next; app/api/orders imports the PostgreSQL client
```

## Verifying framework idioms before flagging

Before filing a finding that claims a framework or library behaves a certain way (e.g. "this Eloquent relation runs N+1", "this Next.js cache invalidation is wrong", "this React effect leaks"), verify against current docs at the project's pinned version. Memory-based recall of framework behavior is unreliable across versions; patterns that were traps in one major are often fixed in the next.

If the Context7 MCP is available in the harness, use it:

- `resolve-library-id` — resolve the library/framework name (e.g. `react`, `next.js`, `laravel`) to a Context7 library ID.
- `query-docs` — fetch the relevant documentation for that library ID, scoped to a natural-language query, before quoting behavior.

Pin the lookup to the project's actual version. Read `package.json`, `composer.json`, `requirements.txt`, `go.mod`, or `Cargo.toml` to identify the major version, then constrain queries (e.g. "Laravel 11 HasOneOrMany limit eager-load behavior").

If Context7 is unavailable, fall back to the vendor's official docs URL directly via the harness's web fetch tool. **Do not skip verification** — a finding that asserts framework behavior without a citation is worse than no finding, because authors trust review output.

When the verified behavior contradicts the finding's premise, drop the finding and (if reviewing a real diff) add the version-correct behavior to the relevant entry in `review-traps-catalog.md` so the next review starts smarter.

## TypeScript / React (.ts, .tsx, .jsx)

- Hook dependency bugs (stale closures in useEffect)
- `any` escape hatches -- flag each with a concrete type suggestion
- Unchecked nullable access (`?.` chains that silently swallow nulls)
- Missing `key` props in mapped JSX
- Effects without cleanup (subscriptions, timers, event listeners)
- `typeof x === "number"` used as a validity check -- it admits `NaN`, `Infinity`, and finite-but-unusable magnitudes. Narrow to the range the consumer accepts (`Number.isFinite`, plus an explicit bound where one exists); `new Date(1e300).toISOString()` throws `RangeError`, and a bare `z.number()` needs `.finite()`

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

## Shell (.sh, .bash, non-GitHub-Actions CI configs)

- Unquoted variables (`$var` vs `"$var"`)
- Missing `set -euo pipefail`
- Command injection via unsanitized input in `eval` or backticks
- `cd` without error check -- use `cd dir || exit 1`
- Hardcoded paths that should be variables

## GitHub Actions (.github/workflows/*.yml)

Reviews the *reviewed repository's* CI, not the harness the review runs under.

- `pull_request_target` combined with a checkout of the PR head (`ref: github.event.pull_request.head.sha` or equivalent) -- runs fork-authored code with a write-scoped token and repository secrets
- Expression interpolation straight into a `run:` block (`${{ github.event.issue.title }}`, `.head_ref`, `.body`, `.comment.body`) -- attacker-controlled text is substituted before the shell parses the script. Route the value through `env:` and reference it as a shell variable
- Third-party action pinned to a mutable ref (tag or branch) instead of a full commit SHA
- `permissions: write-all`, or no `permissions:` key at all so the job inherits the repository default
- Jobs with no `timeout-minutes` -- a hung job holds a runner until the 6-hour ceiling
- Misspelled action inputs (`fetch-detph`, `fetch_depth`) -- unknown `with:` keys are **silently ignored**, not errors, so the step runs with the default and the intent is lost

Scope the pinning check before filing it: report a mutable ref only for a **third-party** action in a **privileged** job -- one holding secrets, an OIDC token, a write-scoped `GITHUB_TOKEN`, or release/deploy/publish/signing power. First-party `actions/*` and `github/*` on a version tag, same-repo `./.github/actions/...` refs, and unprivileged read-only jobs are not findings. When ownership is unclear, treat anything outside `actions/*`, `github/*`, and local paths as third-party.

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
