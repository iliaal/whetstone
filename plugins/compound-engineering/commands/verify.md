---
name: verify
description: Run comprehensive pre-PR verification (build, types, lint, tests, security scan, diff review)
argument-hint: "[mode: quick|full|pre-commit|pre-pr]"
---

# Verify

Run a structured verification pipeline and produce a single READY / NOT READY report.

## Mode

`$ARGUMENTS` -- defaults to `full` if omitted.

| Mode | What runs |
|------|-----------|
| `quick` | Build + type check only |
| `full` | Build + types + lint + tests |
| `pre-commit` | Build + types + lint + tests + console.log audit |
| `pre-pr` | Build + types + lint + tests + console.log audit + security scan + diff review |

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

Record: pass/fail + warning/error counts.

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

Search changed files for:
- Hardcoded secrets (API keys, tokens, passwords in string literals)
- `.env` files staged for commit
- `dangerouslySetInnerHTML`, `eval()`, raw SQL string concatenation

Report: file:line for each finding. These ARE blockers.

### 7. Diff Review (pre-pr only)

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
| Diff review | OK/[N concerns] | [summary] |

### Blockers
- [list any failures or security findings]

### Warnings
- [list non-blocking concerns]
```

If NOT READY, list exactly what needs fixing before the PR can proceed.

## Integration

For in-session verification gates (before claiming tasks complete, committing, or creating PRs), use the `verification-before-completion` skill. This command runs the full pipeline; the skill enforces the discipline of running it.
