# Monorepo Handling

## Discovery (authoring)

Before invoking any `update-*` or `init-*` workflow on a multi-package repo, enumerate every package root that should own an AGENTS.md / README.md. Authoring is recursive by default; pass `--root-only` to collapse back to the repo root.

**Resolve the repository root once:**

```bash
git rev-parse --show-toplevel
```

**Find existing context files to refresh (`update-*` discovery):**

```bash
git ls-files --cached --others --exclude-standard \
  -- '**/README.md' 'README.md' '**/AGENTS.md' 'AGENTS.md'
```

**Find package roots that should get a new file (`init-*` discovery):** package roots are directories holding a language/tooling manifest: the repo root plus the unique directories of these files:

```bash
git ls-files --cached --others --exclude-standard \
  -- '**/package.json' 'package.json' '**/Cargo.toml' 'Cargo.toml' \
     '**/pyproject.toml' 'pyproject.toml' '**/setup.py' 'setup.py' \
     '**/go.mod' 'go.mod' '**/composer.json' 'composer.json'
```

If the repo uses workspace globs (`pnpm-workspace.yaml`, `package.json` `workspaces:`, `Cargo.toml` `[workspace]`, `go.work`), prefer those as ground truth over file enumeration; they declare the canonical package set and avoid false positives from nested vendored manifests.

**Always exclude during discovery:** `.git`, `node_modules`, `vendor`, `.venv`, `target`, `dist`, `build`, `out`, `.next`, `coverage`, anything ignored by git, and hidden dot-directories that lack a manifest.

## Per-file scoping

Treat each target independently:

- The metadata source is the nearest enclosing manifest (the one in its own directory; otherwise walk up to the repo root).
- A nested `README.md` links to its **sibling** `AGENTS.md`, not the root one.
- When CLAUDE.md symlinks are in use (optional; see [Claude Code compatibility](./init-agents.md#claude-code-compatibility)), each `AGENTS.md` gets its sibling `CLAUDE.md` symlink in the **same** directory (`ln -s AGENTS.md CLAUDE.md`, run from that directory). Match the repo's existing convention; keep existing symlinks unless the user asks to remove them. Under the default setting, a root `CLAUDE.md` symlink means every package `AGENTS.md` needs its own sibling symlink or import, or it does not load.
- `CONTRIBUTING.md` is checked per directory; apply the merge advisory from the Update CONTRIBUTING section of SKILL.md.

Process deepest-first or root-first consistently, and report results grouped by path.

## Context loading rules

Claude Code's context-file loading in monorepos follows three rules, and they determine where content belongs. Under the default **Project instructions** setting, AGENTS.md loads only when no `CLAUDE.md`, `.claude/CLAUDE.md`, or `CLAUDE.local.md` exists in the working directory or above it, and a lazily loaded subdirectory AGENTS.md also requires that subdirectory to have none of the three (see [Claude Code compatibility](./init-agents.md#claude-code-compatibility)):

- **Ancestors load immediately**: walking UP from the current working directory, every CLAUDE.md encountered is loaded at startup, and every AGENTS.md too when the condition above holds. Put shared conventions at the repo root.
- **Descendants load lazily**: a CLAUDE.md or AGENTS.md deeper in the tree loads only when Claude reads a file inside that subtree. Put package-specific conventions at each package's root (`packages/api/AGENTS.md`, `apps/web/AGENTS.md`).
- **Siblings never load**: `packages/a/AGENTS.md` will NOT auto-load when working in `packages/b/`. Do not rely on sibling-package context leaking across.

Implication for monorepo layouts: duplicate any rule that must apply across sibling packages into each package's AGENTS.md (or hoist it to the repo root). The loader will not discover it laterally. Conversely, avoid putting package-specific rules at the root; they'll load into every session regardless of relevance and burn context.
