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

Manage project documentation by verifying against actual codebase state: analyze structure, files, and patterns before writing; never generate blind.

## Working rules

- Read existing documentation and verify its claims against actual code and commands before editing.
- Preserve request authority, external-action boundaries, proof standards, and failure-attribution rules when condensing context.
- Do not create CONTRIBUTING.md or DOCS.md as a side effect; apply the specific workflow's creation limits.
- Keep cross-cutting conventions discoverable in the main context file and avoid duplicated volatile facts.
- Report actual edits and checks; do not claim snippets or external identifiers verified without checking them.

## Portability

AGENTS.md is the universal context file (works with Claude Code, Codex, Kilocode). During Initialize Context or Update Context Files workflows only: if CLAUDE.md exists without AGENTS.md, confirm with the user first (Ask via AskUserQuestion (Claude Code; load with ToolSearch `select:AskUserQuestion` if not loaded) or request_user_input (Codex); fall back to numbered options in chat), then `mv CLAUDE.md AGENTS.md`. Never migrate as a side effect of another task.

The CLAUDE.md symlink is optional compatibility, not a required step. Claude Code v2.1.277 and later reads AGENTS.md natively when no `CLAUDE.md`, `.claude/CLAUDE.md`, or `CLAUDE.local.md` exists in the working directory or above it; any of those three found there silently stops that loading, so flag it. For harnesses or sessions that read only CLAUDE.md, offer a CLAUDE.md containing `@AGENTS.md`; offer `ln -s AGENTS.md CLAUDE.md` only when no contributor uses Windows (a clone without `core.symlinks` gets a one-line text file); Edit/Write refuse to write through the link. Keep an existing symlink unless the user asks to remove it. Details and fixes: [init-agents.md](./references/init-agents.md), section "Claude Code compatibility".

When this skill references "context files", it means AGENTS.md (and CLAUDE.md if present, as a symlink or an `@AGENTS.md` import).


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

## Task-specific references

Read the relevant reference before implementing or reviewing the matching behavior:

- For updating or initializing a context file, README, CONTRIBUTING, or API documentation: [documentation-workflows.md](./references/documentation-workflows.md).
- For selecting durable context, organizing documentation, or editing prose: [context-content-and-writing.md](./references/context-content-and-writing.md).

Existing specialized references, when the corresponding topic applies:

- [update-agents.md](./references/update-agents.md).
- [update-readme.md](./references/update-readme.md).
- [update-contributing.md](./references/update-contributing.md).
- [init-agents.md](./references/init-agents.md).
