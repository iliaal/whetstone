# Language-Specific Review Profiles

Contents: [routing](#deterministic-stack-routing) · [framework verification](#verifying-framework-idioms-before-flagging) · [TypeScript/React](#typescript--react-ts-tsx-jsx) · [Python](#python-py-pyi) · [PHP](#php-php) · [Shell](#shell-sh-bash-non-github-actions-ci-configs) · [GitHub Actions](#github-actions-githubworkflowsyml) · [Agent packages](#agent-packages) · [MCP configuration](#mcp-configuration) · [Configuration](#configuration-env-yml-yaml-json-toml) · [Data](#data-formats-csv-json-ingestion-parsers) · [Security](#security-all-files) · [LLM boundaries](#llm-trust-boundaries)

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
| `.py` or `.pyi` | `ia-python-services` |
| `.php` plus `laravel/framework`, `artisan`, or Laravel application structure | `ia-php-laravel` |
| `.rs`, `Cargo.toml`, or `Cargo.lock` | `ia-rust-systems` |
| `.sh`, `.bash`, or a shell-driven CI step outside `.github/workflows/` | `ia-linux-bash-scripting` |
| `.github/workflows/*.yml` | GitHub Actions profile below (supersedes Shell for these files) |
| `SKILL.md`, `agents/*.md`, `hooks.json`, `.mcp.json`, or `settings.json` in an agent package | Agent package profile below; also apply MCP configuration checks to `.mcp.json` |
| `.mcp.json` outside an agent package, `.cursor/mcp.json`, or `.vscode/mcp.json` | MCP configuration profile below |
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

- `resolve-library-id`: resolve the library/framework name (e.g. `react`, `next.js`, `laravel`) to a Context7 library ID.
- `query-docs`: fetch the relevant documentation for that library ID, scoped to a natural-language query, before quoting behavior.

Pin the lookup to the project's actual version. Read `package.json`, `composer.json`, `requirements.txt`, `go.mod`, or `Cargo.toml` to identify the major version, then constrain queries (e.g. "Laravel 11 HasOneOrMany limit eager-load behavior").

If Context7 is unavailable, fall back to the vendor's official docs URL directly via the harness's web fetch tool. **Do not skip verification**: a finding that asserts framework behavior without a citation is worse than no finding, because authors trust review output.

When verified behavior contradicts the finding's premise, drop the finding. Report the version-correct evidence as a proposed lesson when useful. Edit the relevant entry in [review-traps-catalog.md](./review-traps-catalog.md) only under separate skill-maintenance authority; review alone does not authorize that write.

## TypeScript / React (.ts, .tsx, .jsx)

- Hook dependency bugs (stale closures in useEffect)
- `any` escape hatches: flag each with a concrete type suggestion
- Unchecked nullable access (`?.` chains that silently swallow nulls)
- Missing `key` props in mapped JSX
- Effects without cleanup (subscriptions, timers, event listeners)
- `typeof x === "number"` used as a validity check: it admits `NaN`, `Infinity`, and finite-but-unusable magnitudes. Narrow to the range the consumer accepts (`Number.isFinite`, plus an explicit bound where one exists); `new Date(1e300).toISOString()` throws `RangeError`. In Zod 3, add `.finite()` to `z.number()` when finite values are required; [Zod 4 rejects infinities by default](https://zod.dev/v4/changelog#znumber). Enforce consumer-specific magnitude bounds in either version.
- ISO date-only strings such as `new Date('2026-07-04')` parse at UTC midnight; ISO date-time strings without an offset parse in local time. Local formatting west of UTC can show July 3 for that date-only value. Preserve calendar dates as strings, or format their UTC parse with `timeZone: 'UTC'`.

## Python (.py, .pyi)

- Mutable default arguments (`def f(items=[])`)
- Bare `except:`: always catch specific exceptions
- Missing `async`/`await` (sync call in async context)
- f-string injection in SQL/shell: use parameterized queries
- `type: ignore` without justification
- In `.pyi` stub files, do not report unreferenced variables, annotation-only declarations, or unreferenced parameter names. A stub declares an interface it never executes, so these are expected, not dead code
- The stub exemption does not cover every import. A stub re-exports a name only through the self-alias form (`from foo import bar as bar`, `import foo as foo`) or membership in `__all__`; type checkers treat stub files as if implicit re-export is disabled, so a plain `from foo import bar` exports nothing. An unreferenced non-aliased import in a `.pyi` is therefore a legitimate finding, usually a dropped `as` alias that silently removed `bar` from the stub's public surface, breaking every downstream `from stub import bar`. Report it against the intended surface; do not assume deletion is the fix

## PHP (.php)

- Trace coercion, loose comparison, and truthiness only where they change the intended result under the supported PHP version and actual caller. Treat absent `declare(strict_types=1)` as a standards question unless a concrete failure is shown; scalar argument strictness comes from the calling file.
- Distinguish missing keys, explicit `null`, `false`, `0`, and `"0"` when the contract does. Check whether `isset()`, `empty()`, or a nullable/false-returning API collapses states the consumer needs to distinguish.
- Check reuse of a by-reference `foreach` variable after the loop; a retained alias can overwrite the final element. Confirm a subsequent write and whether `unset()` breaks the alias first.
- Compare array union (`+`), `array_merge()`, and unpacking against the required key precedence and numeric-key behavior; demonstrate the value lost, replaced, or reindexed.
- Follow resource, lock, and transaction ownership through failure paths. Require a lifecycle consequence before reporting missing cleanup; distinguish request-shutdown cleanup from long-running workers and established ownership transfer.
- Trace untrusted values to SQL or model writes and inspect existing bindings, allowlists, and guards. Apply ORM-specific checks only with framework evidence; absence of `$fillable` alone does not prove mass-assignment exposure.

## Shell (.sh, .bash, non-GitHub-Actions CI configs)

- Unquoted variables (`$var` vs `"$var"`)
- Missing `set -euo pipefail`
- Command injection via unsanitized input in `eval` or backticks
- `cd` without error check: use `cd dir || exit 1`
- Hardcoded paths that should be variables
- Deploy credentials in unprotected or unmasked CI variables, or deploy jobs allowed on unprotected branches/tags. Protect and mask deploy variables, and restrict deployment to protected refs.
- A remote installer piped directly into a shell interpreter: flag only in jobs or image builds that hold secrets. Use the package manager or a pinned release with a verified checksum; apply the fail-open integrity check in [security-patterns.md](./security-patterns.md).
- TLS verification bypasses in CLI/CI: `curl -k`/`--insecure`, `wget --no-check-certificate`, `kubectl --insecure-skip-tls-verify`, `git -c http.sslVerify=false`/`GIT_SSL_NO_VERIFY`, `pip --trusted-host`, or `npm config set strict-ssl false`. Supply the intended CA instead, using the tool's CA option such as `--cacert` or `--certificate-authority`.

## GitHub Actions (.github/workflows/*.yml)

Reviews the *reviewed repository's* CI, not the harness the review runs under.

- `pull_request_target` combined with a checkout of the PR head (`ref: github.event.pull_request.head.sha` or equivalent): runs fork-authored code with a write-scoped token and repository secrets
- Expression interpolation straight into a `run:` block (`${{ github.event.issue.title }}`, `.head_ref`, `.body`, `.comment.body`): attacker-controlled text is substituted before the shell parses the script. Route the value through `env:` and reference it as a shell variable
- Third-party action pinned to a mutable ref (tag or branch) instead of a full commit SHA
- `permissions: write-all`, or no `permissions:` key at all so the job inherits the repository default
- Jobs with no `timeout-minutes`: a hung job holds a runner until the 6-hour ceiling
- Misspelled action inputs (`fetch-detph`, `fetch_depth`): unknown `with:` keys are **silently ignored**, not errors, so the step runs with the default and the intent is lost
- Before reporting a token leak through `actions/upload-artifact`, verify both the credential location for the pinned `actions/checkout` version and its inclusion in the uploaded files or prebuilt archive. [Upload-artifact v4.4.0 and later exclude hidden files by default](https://github.com/actions/upload-artifact/releases/tag/v4.4.0); inspect older versions, `include-hidden-files: true`, and archive contents. [Checkout v6 stores persisted credentials under `RUNNER_TEMP`](https://github.com/actions/checkout/blob/v6/README.md), rather than directly in `.git/config`; check the actual persistence configuration and upload paths. Report exposure only when the artifact includes a usable credential, with impact bounded by its permissions and lifetime.
- `permissions: id-token: write` at workflow level lets any job on any ref, including a fork PR under `pull_request_target`, mint an OIDC token that the cloud-side trust policy may accept. Scope the permission to the deploy job alone and pin the trust policy's subject to a specific ref (e.g. `ref:refs/heads/main`)
- `${{ github.event.* }}` interpolated inside `actions/github-script`'s `script:` is the same injection as in `run:`; pass the value through `env:` and read it back as `process.env.X`
- `issue_comment` command matching without a trusted-author gate (`comment.author_association` restricted to `OWNER`/`MEMBER`/`COLLABORATOR`, or an explicit permission check): inspect privileged commands, PR-head/merge checkouts, and comment interpolation. Author approval alone does not make the checked-out PR code trustworthy.
- Privileged `workflow_run` consumers that execute or deploy fork-produced artifacts, or extract them over workspace scripts: verify the producer's `head_repository` identity and allowed ref. A fork can name its branch `main`, so `head_branch == 'main'` alone is insufficient. Consume untrusted artifacts only as validated data.
- Cache poisoning from untrusted code in base-branch jobs (`pull_request_target`, `issue_comment`, `workflow_run`): require effective cache-write access and a trusted downstream restore path. GitHub's current defaults deny these triggers writes unless a write-capable `cache-mode` overrides them. Ordinary `pull_request` caches belong to the merge ref and cannot be restored by the base branch. Verify the deployed platform's [cache-access rules](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching#cache-access-for-low-trust-workflow-triggers).
- Fork-controlled code reaching a persistent `runs-on: self-hosted` runner: trace retained files, credentials, and network access into later jobs. Require a clean, isolated runner environment for each untrusted job; removing the runner registration alone does not clean reused hardware.

Require an external actor's input path before classifying a workflow issue as an external-attacker finding. `workflow_dispatch` inputs requiring write access, scheduled execution, and protected-branch pushes alone do not supply that path; trace any untrusted data those jobs consume separately.

Scope the pinning check before filing it: report a mutable ref only for a **third-party** action in a **privileged** job (one holding secrets, an OIDC token, a write-scoped `GITHUB_TOKEN`, or release/deploy/publish/signing power). First-party `actions/*` and `github/*` on a version tag, same-repo `./.github/actions/...` refs, and unprivileged read-only jobs are not findings. When ownership is unclear, treat anything outside `actions/*`, `github/*`, and local paths as third-party.

## Agent packages

Apply to agent-consumed packages containing `SKILL.md`, `agents/*.md`, `hooks.json`, `.mcp.json`, or `settings.json`. Inspect execution and persistence paths without running package code:

- Trace automatically executing hooks declared in frontmatter or plugin configuration, including their trigger and granted authority.
- Review `` !`cmd` `` load-time expansion in local/package skill bodies as shell execution before the model reads the instructions; inspect the command and its inputs. See [Claude Code dynamic context injection](https://code.claude.com/docs/en/skills#inject-dynamic-context).
- Resolve symlink targets and flag paths that escape the package boundary.
- Inspect auto-discovered executables (`conftest.py`, `*.test.*`, `postinstall`) and establish which runner or lifecycle loads them.
- Trace writes to agent configuration or memory (`CLAUDE.md`, `settings.json`, hook files) that persist after package uninstall.
- Compare granted tools with the body's actual needs, and compare the description's promised behavior with the instructions; flag unused grants and mismatches.

## MCP configuration

Inspect package selectors in committed MCP launch commands without executing them. Classify direct-selector drift separately from evidence of exploitation:

- **HIGH**: bare package names, `@latest` or other dist-tags, and Docker images without a digest (including version tags).
- **MEDIUM**: npm `^`/`~`/ranges or Python `>=`, `~=`, and wildcard equality such as `==1.*`.
- **SAFE for direct-selector drift only**: an exact package version or Docker `@sha256:` digest. This does not establish package or transitive-dependency safety.
- **REVIEW**: local paths, VCS/URL sources, or ambiguous command parsing.
- Parse `npx --package`, `uvx --from`, `pipx run --spec`, and Docker's image operand separately from option values and executable arguments.
- Recommend a reviewed version or digest from existing evidence; never invent a pin from the registry's current latest release.

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
