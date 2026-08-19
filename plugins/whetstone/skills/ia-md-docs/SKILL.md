---
name: ia-md-docs
class: workflow
description: >-
  Manages project documentation: CLAUDE.md, AGENTS.md, README.md, CONTRIBUTING.md, DOCS.md.
  Use when asked to update, create, or init these context files. Not for general
  markdown editing.
paths: "**/*.md"
---

# Markdown Documentation

Manage project documentation by verifying against actual codebase state -- analyze structure, files, and patterns before writing; never generate blind.

## Portability

AGENTS.md is the universal context file (works with Claude Code, Codex, Kilocode). During Initialize Context or Update Context Files workflows only: if CLAUDE.md exists without AGENTS.md, confirm with the user first (Ask via AskUserQuestion (Claude Code; load with ToolSearch `select:AskUserQuestion` if not loaded) or request_user_input (Codex); fall back to numbered options in chat), then `mv CLAUDE.md AGENTS.md && ln -sf AGENTS.md CLAUDE.md`. Never migrate as a side effect of another task.

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

**Merge advisory.** When CONTRIBUTING.md sits next to an AGENTS.md (repo root or any package root), surface a one-line recommendation: merge the contribution workflow section into the sibling AGENTS.md so the context file owns dev workflow, branch conventions, and review process as a single source of truth. Then suggest the user delete CONTRIBUTING.md after the merge. Never auto-merge and never auto-delete -- the user performs both. Continue the requested workflow regardless; the CONTRIBUTING file is advisory only.

### Update DOCS

If `DOCS.md` exists, treat it as API-level documentation (endpoints, function signatures, type definitions). Verify against actual code the same way as AGENTS.md. Never auto-create DOCS.md -- only update existing.

### Initialize Context

Create AGENTS.md from scratch for projects without documentation. See [init-agents.md](./references/init-agents.md).

1. Analyze project: language, framework, structure, build/test tools
2. Generate terse, expert-to-expert context sections
3. Write AGENTS.md, create CLAUDE.md symlink

## What Belongs in Context Files

Keep AGENTS.md / CLAUDE.md to durable signal. Do NOT enumerate:

- **Installed skills, plugins, or extensions** -- these change with the user's environment, not the project; the list rots within weeks.
- **Tool versions outside the project's source of truth** -- `package.json` engines, `.nvmrc`, `pyproject.toml` Python constraint, `composer.json` PHP version. List the source-of-truth file path; do not duplicate the version inline.
- **Linter / formatter rule restatements** -- if `.eslintrc`, `ruff.toml`, `phpcs.xml` already enforce it, the file is the spec. List the command to run; do not paraphrase rules.
- **README content** -- if information is already in README.md (install, badges, intro), reference it; do not re-paste.

The test: if a fact will be wrong in two months without anyone touching this file, it does not belong here.

What earns the space is the inverse: document what the agent cannot discover by reading the repo -- the unwritten convention, the reason behind a choice, the gotcha no config file confesses. The environment is a source of truth too, so a section restating it is a cache, and a cache earns its load only when the lookup is expensive. Naming the one test command among forty `package.json` scripts is an expensive lookup and belongs here (see Commands below); a raw `ls -R` dump or a paraphrase of `--help` is a cheap one the agent can re-derive on demand. A curated structure note -- what a new top-level directory is *for* -- is not the same thing, and still belongs here.

## Context File Hierarchy

Structure CLAUDE.md (and AGENTS.md) content by priority so the most critical information loads first when context is compacted:

1. **Rules** -- project constraints, forbidden patterns, required conventions. Override everything else.
2. **Tech stack** -- languages, frameworks, package managers (versions: see above).
3. **Commands** -- how to build, test, lint, deploy. Exact commands, not descriptions.
4. **Conventions** -- naming patterns, file organization, architectural decisions.
5. **Boundaries** -- what's off-limits, what requires approval, scope constraints.

Rules that prevent mistakes outweigh background information.

## Monorepos

Multi-package repo? Read [monorepo.md](./references/monorepo.md) before any `update-*`/`init-*` sweep (discovery commands, per-file scoping, context-loading rules). Enumerate targets; if the sweep would create or rewrite more than 3 files, stop: list planned targets and confirm before writing (same ask mechanism as in Portability above).

## Arguments

Treat these as user-request modifiers: apply when the request contains the flag or equivalent phrasing. All workflows support:

- `--dry-run`: preview changes as a diff, write nothing
- `--preserve`: keep existing structure, fix inaccuracies only
- `--minimal`: quick pass, high-level structure only
- `--thorough`: deep analysis of all files

## Backup Handling

Before overwriting: `cp FILE FILE.backup`; never auto-delete backups.

## Writing Style

- **Lead with the answer.** First sentence of each section states the conclusion; reasoning follows. No "In this section, we'll..." preamble.
- **Imperative form** for instructions: "Build the project" not "The project is built" — verify no passive voice in any directive sentence.
- **One directive per sentence.** A rule that bundles two actions gets half-applied: the reader acts on the first clause and the last, and drops the middle. Move any sequence of 3+ steps into a numbered list rather than burying it in prose.
- **`must`/`never` for requirements, `should`/`may` for latitude.** A requirement phrased as "should" reads as optional and gets skipped.
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
- Changelog-speak, in both directions -- forward-looking hype ("now supports", "new in 3.2", "coming soon") and backward-looking narration of a diff ("this replaced the previous approach", "X was refactored to use Y"). A README describes the tool's present tense; a reader without the commit history gets archaeology instead of a description. Version-migration notes belong in CHANGELOG or `docs/`, and CHANGELOG, release notes, migration guides, and decision records are exempt -- being version-scoped is their purpose

## Report Format

After every operation, display a summary:

```
[OK] Updated AGENTS.md
  - Fixed build command
  - Added new directory to structure

[OK] Updated README.md
  - Added installation section
  - Updated badges

[--] CONTRIBUTING.md not found (skipped)
```

## Verify

- Every factual claim in updated docs verified against current codebase
- No stale file paths or component names
- Formatting renders correctly in markdown preview
