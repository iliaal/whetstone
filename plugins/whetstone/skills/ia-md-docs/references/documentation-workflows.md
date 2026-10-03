# Documentation workflows

## Workflows

### Update Context Files

Verify and fix AGENTS.md against the actual codebase. See [update-agents.md](./update-agents.md) for the full verification workflow.

1. Read existing AGENTS.md, extract verifiable claims (paths, commands, structure, tooling)
2. Verify each claim against codebase (`ls`, `cat package.json`, `cat pyproject.toml`, etc.)
3. Fix discrepancies: outdated paths, wrong commands, missing sections, stale structure
4. Discover undocumented patterns (scripts, build tools, test frameworks not yet documented)
5. Report changes

### Update README

Generate or refresh README.md from project metadata and structure. See [update-readme.md](./update-readme.md) for section templates and language-specific patterns.

1. Detect language/stack from config files (package.json, pyproject.toml, composer.json)
2. Extract metadata: name, version, description, license, scripts
3. If README exists and `--preserve`: fix verified inaccuracies in place; retain every section and its order
4. Otherwise, generate sections appropriate to project type (library vs application)
5. Report changes

### Update CONTRIBUTING

Update existing CONTRIBUTING.md only; never auto-create. See [update-contributing.md](./update-contributing.md).

When updating, detect project conventions automatically:
- Package manager from verified `packageManager` configuration, then lock files (package-lock.json → npm, yarn.lock → yarn, pnpm-lock.yaml → pnpm, bun.lock or legacy bun.lockb → bun). Resolve conflicting signals against repository scripts and CI before documenting commands.
- Branch conventions from git history (feature/, fix/, chore/ prefixes)
- Test commands from package.json scripts or pyproject.toml

**Merge advisory.** When CONTRIBUTING.md sits next to an AGENTS.md (repo root or any package root), surface a one-line recommendation: merge the contribution workflow section into the sibling AGENTS.md so the context file owns dev workflow, branch conventions, and review process as a single source of truth. Then suggest the user delete CONTRIBUTING.md after the merge. Never auto-merge and never auto-delete; the user performs both. Continue the requested workflow regardless; the CONTRIBUTING file is advisory only.

### Update DOCS

If `DOCS.md` exists, treat it as API-level documentation (endpoints, function signatures, type definitions). Verify against actual code the same way as AGENTS.md. Never auto-create DOCS.md; only update existing.

When a doc prescribes a machine-consumed shape (a JSON artifact, config file, or request body), compare the documented shape against the validator's actual source of truth. Use existing schemas, validator constants, or introspection sourced from those definitions. Check both directions: documented keys the validator rejects and required keys the examples omit. Treat an unclassifiable example or a validated artifact with no example as a comparison failure. If the tool lacks introspection, inspect its validator definitions. Report any remaining verification gap. Propose a new reporting subcommand separately. Implement it only when the caller authorized that product change.

- Assert nested rows separately; a walk over top-level examples cannot reach a row inside an array.
- Assert field order when the doc's order is how a reader learns the shape.
- When an existing interface supports the comparison, check the installed binary as well as the build tree. Report unavailable interfaces or artifacts instead of adding them under documentation-only authority.

### Initialize Context

Create AGENTS.md from scratch for projects without documentation. See [init-agents.md](./init-agents.md).

1. Analyze project: language, framework, structure, build/test tools
2. Generate terse, expert-to-expert context sections
3. Write AGENTS.md; create the CLAUDE.md symlink only when needed (optional, see [init-agents.md](./init-agents.md#claude-code-compatibility))
