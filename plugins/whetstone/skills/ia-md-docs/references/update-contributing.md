# Update CONTRIBUTING Workflow

Update existing CONTRIBUTING.md only. Never auto-create -- contribution guidelines represent intentional maintainer decisions.

## Prerequisite

```bash
test -f CONTRIBUTING.md && echo "exists" || echo "missing"
```

If missing: report to user and stop. Do not create unless explicitly requested.

## Scope of Updates

**Fix** (technical accuracy):
- Outdated CLI commands (npm → pnpm, yarn → bun)
- Incorrect file paths or directory references
- Broken links to issues, templates, or docs
- Stale branch references (master → main)
- Wrong tooling references (Jest → Vitest, ESLint → Biome)

**Preserve** (policy decisions):
- Contribution policies (CLA, DCO, licensing)
- Review processes and expectations
- Code of conduct references
- Governance and maintainer decisions
- Communication channel preferences

## Workflow

1. Read existing CONTRIBUTING.md, parse structure and code blocks
2. Detect current tooling: package manager (from lock files), available scripts, branch conventions, linter/formatter config
3. Compare documented commands, paths, links against actual codebase
4. Fix technical inaccuracies while preserving structure and policies
5. Use Edit tool for targeted replacements, not full rewrites

## Adding Acknowledgements

If requested, add or update an Acknowledgements/Credits section. Place at the end, before License if present. Keep it factual -- list contributors, tools, or inspirations without embellishment.

## Report

```
✓ Updated CONTRIBUTING.md
  - Fixed package manager: npm → pnpm
  - Corrected branch reference: master → main
  - Updated test command

⊘ Policy sections preserved (CLA, review process)
```
