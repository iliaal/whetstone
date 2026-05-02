---
name: ia-verify
description: "Run pre-PR verification chain: build, types, lint, tests, security scan, diff review"
argument-hint: "[mode: quick|full|pre-commit|pre-pr]"
---

# Verify

Run a structured verification pipeline and produce a single READY / NOT READY report.

**Boundary vs `/ia-review`:** `/ia-verify` is the pre-PR static gate (pass/fail on build/types/lint/tests/security). `/ia-review` is the multi-agent code review with findings synthesis. Use `/ia-verify` first to confirm shippable; use `/ia-review` for design-level assessment.

## Mode

`$ARGUMENTS` -- defaults to `full` if omitted.

| Mode | What runs |
|------|-----------|
| `quick` | Build + type check only |
| `full` | Build + types + lint + tests |
| `pre-commit` | Build + types + lint + tests + console.log audit |
| `pre-pr` | Build + types + lint + tests + console.log audit + security scan + performance + accessibility + infrastructure + documentation + diff review |

## Applicability Detection

Before running the pipeline, classify the change scope from the diff:

1. Run `git diff --name-only` (or `git diff --cached --name-only` for pre-commit) to get changed files.
2. Classify:
   - **frontend** -- files under `src/components/`, `src/pages/`, `app/`, `*.tsx`, `*.jsx`, `*.vue`, `*.svelte`, `*.css`, `*.scss`, templates
   - **backend** -- files under `src/api/`, `routes/`, `controllers/`, `services/`, `*.php`, `*.py` (non-frontend), `*.go`, server-side TS
   - **infrastructure** -- migration files, Dockerfiles, terraform/ansible, CI configs, env templates, k8s manifests
   - **docs-only** -- only `.md`, `.txt`, `CHANGELOG`, `README` files changed

3. Apply phase filters (pre-pr mode only):
   - **Performance** -- skip for docs-only changes
   - **Accessibility** -- skip for backend-only or docs-only changes
   - **Infrastructure** -- skip for pure frontend changes (no migrations, no env changes, no CI changes)
   - **Documentation** -- always run when user-facing files changed; skip for internal refactors with no API/behavior change

Log which phases were skipped and why in the report.

## Pipeline

Run each phase in order. Stop on the first failure unless the mode skips that phase.

### 1. Build

Detect and run the project's build command:
- `package.json` → `npm run build` (or pnpm/yarn/bun equivalent)
- `Makefile` → `make build`
- `pyproject.toml` → `python -m build` or framework-specific
- `mix.exs` → `mix compile --warnings-as-errors`
- `go.mod` → `go build ./...`
- `composer.json` → `composer install`

Record: pass/fail + error output.

### 2. Type Check (skip for dynamically typed projects without type tooling)

- TypeScript → `npx tsc --noEmit`
- Python with mypy/pyright → run the configured checker
- Go → already covered by build

Record: pass/fail + error count.

### 3. Lint

Detect and run the project's linter:
- Biome, ESLint, Prettier → whichever is configured
- Ruff, Flake8 → for Python
- `golangci-lint run` → for Go
- PHPStan, PHP-CS-Fixer → for PHP

Compare warning counts against the base branch when possible (`git stash && lint && git stash pop` or lint the base ref). Flag any net-new warnings even if the overall run passes.

Record: pass/fail + warning/error counts + new warnings introduced (if measurable).

### 4. Tests

Run the project's test suite:
- `npm test`, `pytest`, `go test ./...`, `php artisan test`, `mix test`, etc.

Record: pass/fail + test count + coverage if available.

### 5. Console.log / Debug Audit (pre-commit and pre-pr only)

Search staged or changed files for debug statements that shouldn't ship:
- `console.log`, `console.debug`, `debugger` (JS/TS)
- `print(`, `breakpoint()`, `pdb.set_trace()` (Python)
- `dd(`, `dump(`, `ray(` (PHP)
- `fmt.Println` used for debugging (Go)

Report: file:line for each occurrence. These are warnings, not blockers.

### 6. Security Scan (pre-pr only)

**6a. Dependency audit** -- run the project's dependency auditor:
- `npm audit` / `pnpm audit` / `yarn audit` (JS/TS)
- `pip-audit` or `safety check` (Python)
- `composer audit` (PHP)
- `govulncheck ./...` (Go)

Flag critical/high vulnerabilities as blockers. Moderate/low are warnings.

**6b. Secrets in diff** -- search changed files for:
- Hardcoded secrets (API keys, tokens, passwords in string literals)
- `.env` files staged for commit
- `dangerouslySetInnerHTML`, `eval()`, raw SQL string concatenation

**6c. Auth/authz review** -- if the diff touches authentication or authorization code (middleware, guards, policies, permission checks, token handling, session management), flag for manual review. Check that:
- No auth bypass paths introduced (missing middleware on new routes)
- Permission checks not weakened or removed
- Token/session expiry not extended without justification

Report: file:line for each finding. Secrets and critical dependency vulnerabilities ARE blockers. Auth changes are warnings requiring human sign-off.

### 7. Performance (pre-pr only, skip for docs-only changes)

Scan the diff for common performance regressions:

- **N+1 queries** -- loops containing database calls where a batch/join/eager-load would work. Look for ORM calls inside `foreach`/`for`/`map`/`array_map` or equivalent.
- **Unbounded queries** -- `SELECT` without `LIMIT`, `findAll()` without pagination, collection fetches with no ceiling. Flag when the table could grow large.
- **Bundle size** (frontend changes) -- check if new dependencies were added (`package.json` diff). For large additions (>50KB gzipped), flag for justification. Run `npm run build` and compare output size if a build-stats script exists.
- **Missing indexes** -- if new queries filter or join on columns, check that indexes exist (or are added in accompanying migrations).

Report: file:line for each concern. These are warnings, not blockers, unless an unbounded query hits a table known to be large.

### 8. Accessibility (pre-pr only, skip for backend-only and docs-only changes)

If the diff includes frontend markup or component changes:

- **Keyboard navigation** -- interactive elements (`button`, `a`, custom clickable divs) must be focusable and operable via keyboard. Flag `onClick` on non-interactive elements without `role`, `tabIndex`, and `onKeyDown`.
- **ARIA attributes** -- custom interactive elements (dropdowns, modals, tabs, accordions) need appropriate `role`, `aria-label`/`aria-labelledby`, and state attributes (`aria-expanded`, `aria-selected`).
- **Contrast** -- if color values changed in the diff (CSS/Tailwind custom colors), flag for contrast ratio verification (4.5:1 text, 3:1 large text).
- **Image alt text** -- new `<img>` tags or `Image` components must have non-empty `alt` (or explicit `alt=""` for decorative images with `aria-hidden`).

Report: file:line for each finding. These are warnings. Skip this phase entirely if no frontend markup was changed.

### 9. Infrastructure (pre-pr only, skip for pure frontend changes)

Check for operational readiness when the diff touches backend, config, or deployment files:

- **Environment variables** -- if new env vars are referenced in code, verify they are documented (`.env.example`, README, or deployment docs). Flag undocumented vars.
- **Migrations** -- if database migration files are present, check that they are reversible (have a `down`/`rollback` method). Flag destructive migrations (dropping columns/tables) without a data preservation strategy.
- **Rollback plan** -- for risky changes (new service dependencies, major schema changes, feature flag removals), flag the need for a rollback plan. Not a blocker, but the report should note it.
- **CI/CD config** -- if CI files changed (`.github/workflows/`, `Jenkinsfile`, `.gitlab-ci.yml`), verify the changes don't break existing pipeline stages.

Report: file:line for each concern. Undocumented env vars are warnings. Irreversible destructive migrations are blockers.

### 10. Documentation (pre-pr only)

Check that documentation keeps pace with code changes:

- **README / CHANGELOG** -- if user-facing behavior changed (new features, changed CLI flags, config options), verify README and/or CHANGELOG are updated in the diff. Flag missing updates.
- **API docs** -- if endpoints were added, changed, or removed, check that API documentation (OpenAPI/Swagger specs, doc comments, or dedicated API docs) reflects the change.
- **Breaking changes** -- if the diff introduces breaking changes (removed endpoints, changed response shapes, renamed config keys), verify they are documented and flagged in CHANGELOG.

Report: list of missing documentation. These are warnings, not blockers, but the report should make them visible.

### 11. Diff Review (pre-pr only)

Run `git diff` against the base branch. Check for:
- Files that changed but have no test coverage
- Large files (>500 lines changed) that may need splitting
- Unrelated changes mixed into the diff

Report: summary of diff scope and any concerns.

## Output

Produce a structured report:

```
## Verification Report

**Mode:** [mode]
**Result:** READY / NOT READY

| Phase | Status | Details |
|-------|--------|---------|
| Build | PASS/FAIL | [summary] |
| Types | PASS/FAIL/SKIP | [summary] |
| Lint | PASS/FAIL/SKIP | [summary] |
| Tests | PASS/FAIL | [N passed, M failed] |
| Debug audit | CLEAN/[N warnings] | [summary] |
| Security | CLEAN/[N findings] | [summary] |
| Performance | OK/[N concerns]/SKIP | [summary] |
| Accessibility | OK/[N concerns]/SKIP | [summary] |
| Infrastructure | OK/[N concerns]/SKIP | [summary] |
| Documentation | OK/[N gaps]/SKIP | [summary] |
| Diff review | OK/[N concerns] | [summary] |

### Blockers
- [list any failures or security findings]

### Warnings
- [list non-blocking concerns]
```

If NOT READY, list exactly what needs fixing before the PR can proceed.

## Integration

For in-session verification gates (before claiming tasks complete, committing, or creating PRs), use the `ia-verification-before-completion` skill. This command runs the full pipeline; the skill enforces the discipline of running it.
