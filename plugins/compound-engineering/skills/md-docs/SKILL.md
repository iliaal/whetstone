---
name: md-docs
description: >-
  Manages project documentation: CLAUDE.md, AGENTS.md, README.md, CONTRIBUTING.md.
  Use when asked to update, create, or init these context files. Not for general
  markdown editing.
paths: "**/*.md"
---

# Markdown Documentation

Manage project documentation by verifying against actual codebase state. Emphasize verification over blind generation -- analyze structure, files, and patterns before writing.

## Portability

AGENTS.md is the universal context file (works with Claude Code, Codex, Kilocode). If the project uses CLAUDE.md, treat it as a symlink to AGENTS.md or migrate content into AGENTS.md and create the symlink:

```bash
# If CLAUDE.md exists and AGENTS.md doesn't
mv CLAUDE.md AGENTS.md && ln -sf AGENTS.md CLAUDE.md
```

When this skill references "context files", it means AGENTS.md (and CLAUDE.md if present as symlink).

## Workflows

### Update Context Files

Verify and fix AGENTS.md against the actual codebase. See [update-agents.md](./references/update-agents.md) for the full verification workflow.

1. Read existing AGENTS.md, extract verifiable claims (paths, commands, structure, tooling)
2. Verify each claim against codebase (`ls`, `cat package.json`, `cat pyproject.toml`, etc.)
3. Fix discrepancies: outdated paths, wrong commands, missing sections, stale structure
4. Discover undocumented patterns (scripts, build tools, test frameworks not yet documented)
5. Report changes

### Update README

Generate or refresh README.md from project metadata and structure. See [update-readme.md](./references/update-readme.md) for section templates and language-specific patterns.

1. Detect language/stack from config files (package.json, pyproject.toml, composer.json)
2. Extract metadata: name, version, description, license, scripts
3. If README exists and `--preserve`: keep custom sections (About, Features), regenerate standard sections (Install, Usage)
4. Generate sections appropriate to project type (library vs application)
5. Report changes

### Update CONTRIBUTING

Update existing CONTRIBUTING.md only -- never auto-create. See [update-contributing.md](./references/update-contributing.md).

When updating, detect project conventions automatically:
- Package manager from lock files (package-lock.json → npm, yarn.lock → yarn, pnpm-lock.yaml → pnpm, bun.lockb → bun)
- Branch conventions from git history (feature/, fix/, chore/ prefixes)
- Test commands from package.json scripts or pyproject.toml

### Update DOCS

If `DOCS.md` exists, treat it as API-level documentation (endpoints, function signatures, type definitions). Verify against actual code the same way as AGENTS.md. Never auto-create DOCS.md -- only update existing.

### Initialize Context

Create AGENTS.md from scratch for projects without documentation. See [init-agents.md](./references/init-agents.md).

1. Analyze project: language, framework, structure, build/test tools
2. Generate terse, expert-to-expert context sections
3. Write AGENTS.md, create CLAUDE.md symlink

## Context File Hierarchy

Structure CLAUDE.md (and AGENTS.md) content by priority so the most critical information loads first when context is compacted:

1. **Rules** -- project constraints, forbidden patterns, required conventions. Override everything else.
2. **Tech stack** -- languages, frameworks, versions, package managers.
3. **Commands** -- how to build, test, lint, deploy. Exact commands, not descriptions.
4. **Conventions** -- naming patterns, file organization, architectural decisions.
5. **Boundaries** -- what's off-limits, what requires approval, scope constraints.

Rules that prevent mistakes outweigh background information. Place them at the top so they survive aggressive context compaction.

## Arguments

All workflows support:

- `--dry-run`: preview changes without writing
- `--preserve`: keep existing structure, fix inaccuracies only
- `--minimal`: quick pass, high-level structure only
- `--thorough`: deep analysis of all files

## Backup Handling

Before overwriting, back up existing files:

```bash
cp AGENTS.md AGENTS.md.backup
cp README.md README.md.backup
```

Never delete backups automatically.

## Writing Style

- **Lead with the answer.** First sentence of each section states the conclusion; reasoning follows. No "In this section, we'll..." preamble.
- **Imperative form** for instructions: "Build the project" not "The project is built" — verify no passive voice in any directive sentence.
- **Expert-to-expert**: cut explanations of concepts the target reader already knows. For CLAUDE.md/AGENTS.md, assume familiarity with git, package managers, test runners, and the project's main language.
- **Scannable**: headings every ~20 lines, bullet lists for ≥3 parallel items, fenced code blocks for every command.
- **Verify every command and path against the codebase.** Run each command before committing; grep for each referenced path. Stale paths and untested commands are the most common doc defect.
- **Sentence case headings**, no emoji decoration (exception: changelog entries may use emoji per project convention).
- **Actionable headings**: "Set SAML before adding users" — not "SAML configuration timing". Reader should know what to do from the heading alone.
- **Collapse depth** with `<details>` blocks instead of deleting content (blank line required after `<summary>` for GitHub rendering).

## README Anti-Patterns

Flag during `Update README` workflows:
- Framework-first lead (explaining the tech stack before the problem it solves)
- Jargon before definition (using project-specific terms without introduction)
- Theory before try (architecture explanation before a working example)
- Claims without evidence ("blazingly fast" with no benchmarks)

## Report Format

After every operation, display a summary:

```
✓ Updated AGENTS.md
  - Fixed build command
  - Added new directory to structure

✓ Updated README.md
  - Added installation section
  - Updated badges

⊘ CONTRIBUTING.md not found (skipped)
```

## Verify

- Every factual claim in updated docs verified against current codebase
- No stale file paths or component names
- Formatting renders correctly in markdown preview
