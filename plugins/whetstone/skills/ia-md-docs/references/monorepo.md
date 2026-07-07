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

**Find package roots that should get a new file (`init-*` discovery):** package roots are directories holding a language/tooling manifest -- the repo root plus the unique directories of these files:

```bash
git ls-files --cached --others --exclude-standard \
  -- '**/package.json' 'package.json' '**/Cargo.toml' 'Cargo.toml' \
     '**/pyproject.toml' 'pyproject.toml' '**/setup.py' 'setup.py' \
     '**/go.mod' 'go.mod' '**/composer.json' 'composer.json'
```

If the repo uses workspace globs (`pnpm-workspace.yaml`, `package.json` `workspaces:`, `Cargo.toml` `[workspace]`, `go.work`), prefer those as ground truth over file enumeration — they declare the canonical package set and avoid false positives from nested vendored manifests.

**Always exclude during discovery:** `.git`, `node_modules`, `vendor`, `.venv`, `target`, `dist`, `build`, `out`, `.next`, `coverage`, anything ignored by git, and hidden dot-directories that lack a manifest.

## Per-file scoping

Treat each target independently:

- The metadata source is the nearest enclosing manifest (the one in its own directory; otherwise walk up to the repo root).
- A nested `README.md` links to its **sibling** `AGENTS.md`, not the root one.
- Each `AGENTS.md` gets a sibling `CLAUDE.md` symlink in the **same** directory (`ln -sf AGENTS.md CLAUDE.md`, run from that directory).
- `CONTRIBUTING.md` is checked per directory; apply the merge advisory from the Update CONTRIBUTING section of SKILL.md.

Process deepest-first or root-first consistently, and report results grouped by path.

## Context loading rules

Claude Code's context-file loading in monorepos follows three rules -- understanding them determines where content belongs:

- **Ancestors load immediately**: walking UP from the current working directory, every AGENTS.md / CLAUDE.md encountered is loaded at startup. Put shared conventions at the repo root.
- **Descendants load lazily**: an AGENTS.md deeper in the tree loads only when Claude reads or edits a file inside that subtree. Put package-specific conventions at each package's root (`packages/api/AGENTS.md`, `apps/web/AGENTS.md`).
- **Siblings never load**: `packages/a/AGENTS.md` will NOT auto-load when working in `packages/b/`. Do not rely on sibling-package context leaking across.

Implication for monorepo layouts: duplicate any rule that must apply across sibling packages into each package's AGENTS.md (or hoist it to the repo root). The loader will not discover it laterally. Conversely, avoid putting package-specific rules at the root -- they'll load into every session regardless of relevance and burn context.
