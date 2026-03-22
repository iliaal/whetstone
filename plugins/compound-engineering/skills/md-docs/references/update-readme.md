# Update README Workflow

Generate or refresh README.md based on codebase analysis.

## Guiding Principles

- Balanced, not bloated: 200-400 lines for most projects
- Show, don't tell: code examples over prose
- Every section must add value -- skip empty or trivial sections
- Readers should find what they need in under 30 seconds

Target length: `--minimal` 100-200 lines, default 200-400, `--thorough` 400-600.

## Language/Stack Detection

| Signal | Stack |
|--------|-------|
| `package.json` | Node.js / TypeScript / JavaScript |
| `pyproject.toml`, `setup.py` | Python |
| `composer.json` | PHP |
| `*.pine` files | PineScript |
| `*.sh`, `Makefile` | Bash / Shell |

**Extract from config files:** name, version, description, license, dependencies, scripts, repo URL.

**Detect package manager from lock files:**
- `package-lock.json` → npm
- `pnpm-lock.yaml` → pnpm
- `yarn.lock` → yarn
- `bun.lockb` → bun
- `composer.lock` → composer
- `uv.lock` → uv
- `poetry.lock` → poetry

## Section Order

**Libraries** (exports modules, no main entry):

1. Title + badges
2. Description
3. Features (if `--preserve` or `--thorough`)
4. Installation
5. Usage with code examples
6. API Reference (`--thorough` only)
7. License

**Applications** (has entry point, runnable):

1. Title + badges
2. Description
3. Features
4. Installation / Getting Started
5. Usage
6. Configuration (if config files found)
7. Scripts / Commands
8. Project Structure (`--thorough` only)
9. License

**PineScript indicators/strategies:**

1. Title
2. Description (what it measures/trades)
3. Inputs and parameters
4. Usage (how to add to TradingView chart)
5. Logic overview
6. Alerts (if applicable)

## Section Guidelines

**Title + Badges:** Project name from config or repo name. Add badges for CI (if `.github/workflows/` exists), license, version. Skip badges for private repos.

**Description:** 1-3 sentences. Answer "what does this do?" Extract from config file description field when available.

**Features:** 3-8 bullet points for `--thorough`. Skip if obvious from description. `--minimal` omits this.

**Installation:** Show install command for detected package manager. Include `git clone` if no registry. For PHP: `composer require` or `composer install`.

**Usage:** Minimal working example (5-15 lines). Extract from tests or examples/ directory if they exist. Use proper language tags on code blocks.

**Scripts/Commands:** List from package.json scripts, composer scripts, Makefile targets. Format as table if 5+ items.

**Project Structure:** Only for `--thorough`. Show 5-10 key directories, 2 levels deep max. Skip if structure is obvious.

**Configuration:** Document if .env.example, config files exist. Show key options. Otherwise omit.

## Preserve Mode

When `--preserve` is set and README.md exists:

**Keep** (user-written): About, Features, Why X, Background, custom sections.

**Regenerate** (likely outdated): Install, Usage, Scripts, Structure, Badges, Configuration.

Merge preserved sections with regenerated ones in standard order.

## Formatting

- Sentence case headings, no emoji headers
- `##` for main sections, `###` for subsections
- Code blocks with language tags
- Tables for commands if 5+ items
- Admonitions for important notes: `> [!NOTE]` and `> [!WARNING]`
- No git operations -- user reviews and commits manually
