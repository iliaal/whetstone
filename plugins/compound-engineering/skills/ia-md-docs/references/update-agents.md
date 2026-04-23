# Update Context Files Workflow

Verify and fix AGENTS.md (and CLAUDE.md symlink) against actual codebase state.

## Step 1: Extract Verifiable Claims

Read AGENTS.md and extract every factual claim:

- File paths and directory structures
- Build, test, lint commands
- Dependency and tooling references
- Code conventions and patterns described
- Environment variables or configuration

## Step 2: Verify Claims

Check each claim against the codebase:

**Paths and structure:**
- `ls`, `tree` (2 levels) to verify directories exist
- If path changed: update. If deleted: remove section.

**Commands:**
- Check `package.json` scripts, `composer.json` scripts, `pyproject.toml` scripts, `Makefile`, `justfile`
- If command syntax changed: update. If removed: mark for removal.

**Code patterns:**
- Read actual files to verify described patterns still hold
- Update outdated patterns to match current code

## Step 3: Discover Undocumented Patterns

Scan for patterns not yet in AGENTS.md:

- Task runner recipes (justfile, Makefile, package.json scripts) not documented
- Lint/format configuration that exists but has no corresponding section
- Build/test/deploy commands with no documentation
- New directories or modules not mentioned in structure

## Step 4: Apply Updates

**If `--dry-run`:** show planned changes as diff without writing.

**If `--preserve`:** fix inaccuracies only, keep existing structure and phrasing.

**Otherwise:** reorganize for clarity, add missing sections, remove stale content.

## Step 5: Report

```
✓ Updated AGENTS.md
  - Fixed: build command npm → pnpm
  - Removed: stale reference to /old-dir
  - Added: new /api directory to structure

Suggested additions:
  - Consider documenting: jest test configuration
```

If no changes needed: `✓ AGENTS.md is up to date`
