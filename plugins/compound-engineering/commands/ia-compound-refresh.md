---
name: ia-compound-refresh
description: Review docs/solutions/ for stale learnings -- keep, update, replace, or archive
---

# Compound Refresh

Review institutional knowledge in `docs/solutions/` for drift and staleness.

## Process

### 1. Inventory

List all files in `docs/solutions/` recursively. For each file, read the YAML frontmatter and first 20 lines of content to understand what it documents.

If `docs/solutions/` doesn't exist or is empty, report that and stop.

### 2. Validate references

For each learning doc, check whether the code it references still exists:

- **File paths** mentioned in the doc -- do they still exist?
- **Function/class names** -- grep for them in the codebase
- **Patterns described** -- are they still the current approach?
- **Dependencies/versions** -- still accurate?

### 3. Classify

For each doc, assign one status:

| Status | Criteria | Action |
|--------|----------|--------|
| **Keep** | All references valid, patterns current | No changes |
| **Update** | Partially stale -- some refs outdated but core insight valid | Fix stale references, update code examples |
| **Replace** | Fundamentally wrong -- approach has changed | Rewrite with current approach, preserve the problem statement |
| **Archive** | No longer relevant -- feature removed, problem no longer exists | Move to `docs/solutions/_archive/` |

### 4. Report

Present findings as a table:

```
| File | Status | Issue |
|------|--------|-------|
| performance-issues/n-plus-one.md | Keep | All refs valid |
| auth/session-token-bug.md | Update | `auth.js` renamed to `auth.ts` |
| billing/stripe-webhook.md | Archive | Billing module removed in v3 |
```

### 5. Apply

Ask before making changes: "Apply these updates? (all / pick by number / skip)"

For approved items:
- **Update**: make surgical fixes to stale references
- **Replace**: rewrite the doc, preserving the problem statement
- **Archive**: `mkdir -p docs/solutions/_archive && mv [file] docs/solutions/_archive/`

## Constraints

- Never delete learning docs -- archive them
- Preserve YAML frontmatter structure when updating
- Don't rewrite docs that are still accurate just to "improve" them
