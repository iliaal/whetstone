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

### 4b. Inbound-link check (Archive candidates only)

Before classifying a doc as **Archive**, search the repo's markdown content for citations. A learning that other artifacts cite is load-bearing in a way the doc itself does not announce.

Search both the basename and the path-relative-to-`docs/solutions/` to catch path-qualified citations and avoid false-matching unrelated docs that share a basename across subdirectories:

```bash
rel="${file#docs/solutions/}"          # e.g. "performance-issues/n-plus-one.md"
slug="$(basename "$file" .md)"          # e.g. "n-plus-one"
grep -rn --include='*.md' -e "$rel" -e "$slug" . 2>/dev/null \
  | grep -v "^./$file:"                 # exclude self-references
```

Scope the grep to the repo root, not just `docs/`, so plans, READMEs, AGENTS.md, and other tracked markdown surfaces are checked.

Classify each citation:

- **Decorative** — bare "see also" pointer, attribution, or principle stated inline at the citing site. Archive is fine; clean up the citations in the same pass.
- **Substantive** — the citing doc relies on the cited doc to provide content not stated inline ("see X for the full procedure" with no inline procedure). Downgrade to **Replace** (rewrite at the same path with the current approach) or **Update** (narrow scope to what's still useful).
- **Mixed or unclear** — surface the citations to the user and ask before archiving.

If any substantive citation exists, do not archive without writing a successor or surfacing the conflict. The successor preserves the inbound link target; an unannounced archive leaves the citation pointing at `_archive/`.

### 4c. Cross-file edit disclosure

If Step 4b classifies any citations as decorative (cleanup-on-archive) or substantive (repoint-to-successor), append a **Cross-file edits** section to the Step 4 report listing every non-`docs/solutions/` file the apply pass will touch:

```
| File | Citation | Edit |
|------|----------|------|
| docs/plans/2026-04-12-feat-x-plan.md | line 42 | drop "see auth/session-token-bug" |
| AGENTS.md | line 88 | repoint to `docs/solutions/auth/session-bug-v2.md` |
```

The Step 5 apply prompt confirms these explicitly so the user knows the archive pass mutates files outside `docs/solutions/`.

### 5. Apply

Ask before making changes: "Apply these updates? (all / pick by number / skip). Note: any cross-file edits listed in Step 4c will be applied alongside the Archive."

For approved items:
- **Update**: make surgical fixes to stale references
- **Replace**: rewrite the doc, preserving the problem statement
- **Archive**: `mkdir -p docs/solutions/_archive && mv [file] docs/solutions/_archive/` — then apply any Cross-file edits from Step 4c (drop decorative citations, repoint substantive citations to the successor doc).

## Constraints

- Never delete learning docs -- archive them
- Preserve YAML frontmatter structure when updating
- Don't rewrite docs that are still accurate just to "improve" them
