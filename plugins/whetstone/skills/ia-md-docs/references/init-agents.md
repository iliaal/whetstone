# Initialize Context Workflow

Create AGENTS.md from scratch for projects without documentation.

## Check Existing

```bash
test -f AGENTS.md && echo "exists" || echo "missing"
test -f CLAUDE.md && echo "claude exists" || echo "no claude"
```

If AGENTS.md exists: warn user, suggest update workflow instead. Allow override with `--force`.

If CLAUDE.md exists but AGENTS.md doesn't: migrate (rename to AGENTS.md; add a CLAUDE.md symlink only if a harness or session needs it, per [Claude Code compatibility](#claude-code-compatibility)).

If a `CLAUDE.md`, `.claude/CLAUDE.md`, or `CLAUDE.local.md` exists in the working directory or above it, report that it stops Claude Code from loading AGENTS.md by default.

## Claude Code compatibility

Claude Code v2.1.277 and later reads `AGENTS.md` and `.claude/AGENTS.md` in the working directory and above it, but only when none of `CLAUDE.md`, `.claude/CLAUDE.md`, or `CLAUDE.local.md` exists there. The user-level `~/.claude/CLAUDE.md`, a managed `CLAUDE.md`, and `.claude/rules/` files do not count and load alongside AGENTS.md.

| Situation | Action |
|---|---|
| Current Claude Code, no CLAUDE.md | No symlink needed; AGENTS.md loads natively |
| `CLAUDE.local.md` or a real `CLAUDE.md` present | AGENTS.md is not loaded. Either add a CLAUDE.md next to AGENTS.md containing `@AGENTS.md` (or put the import at the top of an existing CLAUDE.md in that directory), or set `/config` **Project instructions** to `claude-md-and-agents-md` (user-level setting) |
| Claude Code before v2.1.277, built-in `agents-md` plugin disabled, first session after upgrading from v2.1.276 or earlier, or (before v2.1.281) some Bedrock or telemetry-disabled sessions | Only CLAUDE.md is read. Offer a CLAUDE.md containing `@AGENTS.md` (Claude-specific lines go below the import). Offer `ln -s AGENTS.md CLAUDE.md` only when no contributor uses Windows: Git checks a committed symlink out there as a one-line text file unless `core.symlinks` is enabled. Edit and Write also refuse to write through a symlink and redirect the edit to AGENTS.md |
| Existing `CLAUDE.md` symlink to AGENTS.md | Leave it unless the user asks to remove it: other harnesses and the sessions in the row above still depend on it. Claude Code reads the content once either way |
| `SessionStart` hook that prints AGENTS.md | Report it: with native loading it adds a second copy to context |

Native loading differs from a symlink or import in two places: `InstructionsLoaded` hooks do not fire for a natively read AGENTS.md (they do fire through a CLAUDE.md symlink or `@AGENTS.md` import), and directories added with `--add-dir` while `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` is set load their CLAUDE.md but not their AGENTS.md. Keep the symlink when either matters.

Use `ln -s`, not `ln -sf`: `-f` replaces a real CLAUDE.md without warning.

## Modes

**Automatic** (no arguments): derive everything from project analysis.

**Guided** (arguments provided): user describes the project focus, e.g. "PHP Laravel API with queue workers" or "Python data pipeline with scheduled jobs".

## Gather Context

Read available config files (skip missing):
- `package.json`: stack, scripts, dependencies
- `pyproject.toml`: Python project config
- `composer.json`: PHP project config
- `README.md`: project overview
- `.gitignore`: exclusion patterns
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
- PHP 8.4+ with Laravel
- Composer for dependencies
- PHPUnit / Pest for testing

## Commands
- `composer install` -- install dependencies
- `php artisan serve` -- local dev server
- `php artisan test` -- run tests
- `php artisan migrate` -- run migrations
```

### Python

```markdown
## Stack
- Python 3.11+
- uv for dependency management

## Commands
- `uv sync` -- install dependencies
- `uv run pytest` -- run tests
- `uv run ruff check .` -- lint
```

### JavaScript / TypeScript

```markdown
## Stack
- TypeScript with strict mode
- {detected package manager}

## Commands
- `{pm} install` -- install dependencies
- `{pm} run build` -- build
- `{pm} test` -- run tests
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
- `shellcheck *.sh` -- lint all scripts
- `chmod +x script.sh && ./script.sh` -- run
```

## Generate Content

Sections to include (only if relevant):

- **Stack**: languages, frameworks, tools
- **Structure**: key directories and files
- **Commands**: build, test, lint, deploy
- **Code style**: naming, formatting, patterns
- **Constraints**: security, performance, environment

Style: terse, imperative, expert-to-expert. No fluff.

Quality rules (SkillsBench arXiv:2602.12670):
- Procedural over declarative: "Run `npm test`" beats "Tests should pass"
- Tables over prose: agents parse structured data more reliably
- 2K-8K chars is optimal (+18.8pp). Beyond 15K, effectiveness degrades. Split or link out.
- Context-first ordering: overview before commands, commands before architecture

## Write

1. Write AGENTS.md with generated content
2. Optional: create the CLAUDE.md symlink (`ln -s AGENTS.md CLAUDE.md`) when the user or a harness needs it (see [Claude Code compatibility](#claude-code-compatibility)); otherwise skip it and say so in the report
3. Report: show file path, preview first 10 lines

```
✓ Created AGENTS.md
✓ Created CLAUDE.md → AGENTS.md symlink (only if step 2 ran)
  - Detected: Python project (pyproject.toml)
  - Sections: Stack, Structure, Commands, Code Style
```
