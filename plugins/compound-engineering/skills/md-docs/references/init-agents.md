# Initialize Context Workflow

Create AGENTS.md from scratch for projects without documentation.

## Check Existing

```bash
test -f AGENTS.md && echo "exists" || echo "missing"
test -f CLAUDE.md && echo "claude exists" || echo "no claude"
```

If AGENTS.md exists: warn user, suggest update workflow instead. Allow override with `--force`.

If CLAUDE.md exists but AGENTS.md doesn't: migrate — rename to AGENTS.md, create CLAUDE.md symlink.

## Modes

**Automatic** (no arguments): derive everything from project analysis.

**Guided** (arguments provided): user describes the project focus, e.g. "PHP Laravel API with queue workers" or "Python data pipeline with scheduled jobs".

## Gather Context

Read available config files (skip missing):
- `package.json` — stack, scripts, dependencies
- `pyproject.toml` — Python project config
- `composer.json` — PHP project config
- `README.md` — project overview
- `.gitignore` — exclusion patterns
- Directory listing (2 levels deep)

Determine:
- Primary language/framework
- Project type: library, application, CLI tool, script collection
- Build/test/lint tools
- Architecture patterns

## Language Templates

### PHP / Laravel

```markdown
## Stack
- PHP 8.2+ with Laravel
- Composer for dependencies
- PHPUnit / Pest for testing

## Commands
- `composer install` — install dependencies
- `php artisan serve` — local dev server
- `php artisan test` — run tests
- `php artisan migrate` — run migrations
```

### Python

```markdown
## Stack
- Python 3.11+
- uv for dependency management

## Commands
- `uv sync` — install dependencies
- `uv run pytest` — run tests
- `uv run ruff check .` — lint
```

### JavaScript / TypeScript

```markdown
## Stack
- TypeScript with strict mode
- {detected package manager}

## Commands
- `{pm} install` — install dependencies
- `{pm} run build` — build
- `{pm} test` — run tests
```

### PineScript

```markdown
## Stack
- Pine Script v6 (TradingView)

## Development
- Edit in TradingView Pine Editor
- Test with bar replay and strategy tester
- No external build tools
```

### Bash / Shell

```markdown
## Stack
- Bash scripts for automation
- ShellCheck for linting

## Commands
- `shellcheck *.sh` — lint all scripts
- `chmod +x script.sh && ./script.sh` — run
```

## Generate Content

Sections to include (only if relevant):

- **Stack** — languages, frameworks, tools
- **Structure** — key directories and files
- **Commands** — build, test, lint, deploy
- **Code style** — naming, formatting, patterns
- **Constraints** — security, performance, environment

Style: terse, imperative, expert-to-expert. No fluff.

Quality rules (SkillsBench arXiv:2602.12670):
- Procedural over declarative — "Run `npm test`" beats "Tests should pass"
- Tables over prose — agents parse structured data more reliably
- 2K-8K chars is optimal (+18.8pp). Beyond 15K, effectiveness degrades. Split or link out.
- Context-first ordering — overview before commands, commands before architecture

## Write

1. Write AGENTS.md with generated content
2. Create CLAUDE.md symlink: `ln -sf AGENTS.md CLAUDE.md`
3. Report: show file path, preview first 10 lines

```
✓ Created AGENTS.md
✓ Created CLAUDE.md → AGENTS.md symlink
  - Detected: Python project (pyproject.toml)
  - Sections: Stack, Structure, Commands, Code Style
```
