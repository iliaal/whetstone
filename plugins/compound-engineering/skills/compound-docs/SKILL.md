---
name: compound-docs
description: >-
  Capture solved problems as categorized documentation with YAML frontmatter
  for fast lookup. Use when documenting a resolved issue, saving a solution for
  reuse, or building searchable institutional knowledge after debugging or
  troubleshooting.
disable-model-invocation: true
allowed-tools:
  - Read # Parse conversation context
  - Write # Create resolution docs
  - Bash # Create directories
  - Grep # Search existing docs
preconditions:
  - Problem has been solved (not in-progress)
  - Solution has been verified working
---

# compound-docs

## Process

Single-file architecture -- one markdown file per problem in its symptom category directory (e.g., `docs/solutions/performance-issues/n-plus-one-briefs.md`), with YAML frontmatter for metadata.

Follow the 7-step documentation capture process. For full details, see [documentation-process.md](./references/documentation-process.md).

1. **Detect confirmation** -- Auto-invoke after "that worked", "it's fixed", etc. Skip trivial fixes.
2. **Gather context** -- Extract module, symptom, investigation attempts, root cause, solution, prevention. BLOCK if critical context missing.
3. **Check existing docs** -- Search `docs/solutions/` for similar issues. If found, offer: new doc with cross-reference, update existing, or other.
4. **Generate filename** -- Format: `[sanitized-symptom]-[module]-[YYYYMMDD].md`
5. **Validate YAML** -- Run [validate-frontmatter.sh](./scripts/validate-frontmatter.sh) against the file. BLOCK until valid.
6. **Create documentation** -- Write file to `docs/solutions/[category]/[filename].md` using [resolution-template.md](./assets/resolution-template.md).
7. **Cross-reference** -- Link related issues. Detect critical patterns (3+ similar issues).

---

## Decision Menu

After successful documentation, present and WAIT for user response:

```
Solution documented

File created:
- docs/solutions/[category]/[filename].md

What's next?
1. Continue workflow (recommended)
2. Add to Required Reading - Promote to critical patterns
3. Link related issues - Connect to similar problems
4. Add to existing skill - Add to a learning skill
5. Create new skill - Extract into new learning skill
6. View documentation - See what was captured
7. Other
```

For detailed response handling, see [documentation-process.md](./references/documentation-process.md).

---

## Integration Points

**Invoked by:** `/workflows:compound` command, manual invocation after solution confirmed, or auto-triggered by confirmation phrases.

**Invokes:** None (terminal skill -- does not delegate to other skills).

**Handoff:** All context needed should be present in conversation history before invocation.

---

## Success Criteria

- YAML frontmatter validated (all required fields, correct formats)
- File created in `docs/solutions/[category]/[filename].md`
- Enum values match schema exactly
- Code examples included in solution section
- Cross-references added if related issues found
- User presented with decision menu and action confirmed

---

## References

- [documentation-process.md](./references/documentation-process.md) - Full 7-step process with validation gates
- [yaml-schema.md](./references/yaml-schema.md) - YAML frontmatter schema and enum values
- [quality-guidelines.md](./references/quality-guidelines.md) - Quality standards, execution rules, error handling
- [example-scenario.md](./references/example-scenario.md) - Complete walkthrough of documenting an N+1 query fix
- [resolution-template.md](./assets/resolution-template.md) - Template for documentation files
- [critical-pattern-template.md](./assets/critical-pattern-template.md) - Template for critical pattern entries
- [validate-frontmatter.sh](./scripts/validate-frontmatter.sh) - Validate YAML frontmatter against schema
