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
3. If README exists and `--preserve`: keep custom sections (About, Features), regenerate standard sections (Install, Usage)
4. Generate sections appropriate to project type (library vs application)
5. Report changes

### Update CONTRIBUTING

Update existing CONTRIBUTING.md only; never auto-create. See [update-contributing.md](./update-contributing.md).

When updating, detect project conventions automatically:
- Package manager from lock files (package-lock.json → npm, yarn.lock → yarn, pnpm-lock.yaml → pnpm, bun.lockb → bun)
- Branch conventions from git history (feature/, fix/, chore/ prefixes)
- Test commands from package.json scripts or pyproject.toml

**Merge advisory.** When CONTRIBUTING.md sits next to an AGENTS.md (repo root or any package root), surface a one-line recommendation: merge the contribution workflow section into the sibling AGENTS.md so the context file owns dev workflow, branch conventions, and review process as a single source of truth. Then suggest the user delete CONTRIBUTING.md after the merge. Never auto-merge and never auto-delete; the user performs both. Continue the requested workflow regardless; the CONTRIBUTING file is advisory only.

### Update DOCS

If `DOCS.md` exists, treat it as API-level documentation (endpoints, function signatures, type definitions). Verify against actual code the same way as AGENTS.md. Never auto-create DOCS.md; only update existing.

When a doc prescribes a machine-consumed shape (a JSON artifact, config file, or request body) that code then validates, the two drift silently and each drift costs one caller a rejected write. A test that greps the doc for key names is a second copy of the doc: it goes green when both copies are wrong together, which is the only failure that matters. Have the tool report its validators' key sets as a versioned subcommand, sourced from the **same constants the validators read** (a constant only the report reads is decoration), then compare the doc against that report in both directions: a documented key no validator accepts, and a required key no example shows. Guard the guard: an example nothing can classify is a failure rather than a skip, and a validated artifact with no example is a failure.

- Assert nested rows separately; a walk over top-level examples cannot reach a row inside an array.
- Assert field order when the doc's order is how a reader learns the shape.
- Run the comparison against the installed binary as well as the build tree.

### Initialize Context

Create AGENTS.md from scratch for projects without documentation. See [init-agents.md](./init-agents.md).

1. Analyze project: language, framework, structure, build/test tools
2. Generate terse, expert-to-expert context sections
3. Write AGENTS.md; create the CLAUDE.md symlink only when needed (optional, see [init-agents.md](./init-agents.md#claude-code-compatibility))
