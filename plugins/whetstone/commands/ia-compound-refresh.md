---
name: ia-compound-refresh
description: "Review docs/solutions/ for stale learnings: keep, update, replace, or archive"
---

# Compound Refresh

Review institutional knowledge in `docs/solutions/` for drift and staleness.

## Process

### 1. Inventory

List all files in `docs/solutions/` recursively. For each file, read the YAML frontmatter and first 20 lines of content to understand what it documents.

If `docs/solutions/` doesn't exist or is empty, report that and stop.

### 2. Validate references

For each learning doc, check whether the code it references still exists:

- **File paths** mentioned in the doc: do they still exist?
- **Function/class names**: grep for them in the codebase
- **Patterns described**: are they still the current approach?
- **Dependencies/versions**: still accurate?

**Unverifiable is not false.** These are existence checks, and a repo rarely witnesses its own operations. A learning about a database tuning practice, a deploy runbook, an environment quirk, or an onboarding step has no greppable in-repo referent and never will. Act on *contradiction* (the repo shows something different from what the doc claims), not on absence of corroboration, and note the verification gap in the report instead of resolving it against the doc.

**Missing files prove the implementation is gone, not the problem.** If the application still deals with what the doc addresses, that is Replace, not Archive. A doc that never referenced in-repo code cannot satisfy "implementation gone" and must never auto-archive on that basis.

**Mechanics follow the code; evidenced guidance does not.** A doc claim about how the system currently works (a path, a function name, a config value) follows the code: when they disagree, the doc is stale. A practice the doc justifies on its own evidence (a measured fix, a post-incident rule, a vendor constraint) does not become false because the implementation stopped satisfying it. Classify that doc from its own evidence (usually Keep) and report the code's drift as a potential regression in the Step 4 report instead of rewriting the practice to match broken code. Refresh edits docs only; it never adjudicates or edits product code.

### 3. Classify

For each doc, assign one status:

| Status | Criteria | Action |
|--------|----------|--------|
| **Keep** | All references valid, patterns current; or evidenced guidance whose enforcing code drifted (per the mechanics-vs-guidance rule above: the doc stands, the drift is reported) | No changes to the doc; note the drift in the report |
| **Update** | Partially stale: some refs outdated but core insight valid | Fix stale references, update code examples |
| **Replace** | Fundamentally wrong: approach has changed | Rewrite with current approach, preserve the problem statement |
| **Archive** | No longer relevant: feature removed, problem no longer exists | Move to `docs/solutions/_archive/` |

### 3b. Worth lens (opt-in, default off)

Run this step only when the request explicitly asks to clean up, cull, prune, or upgrade the store to the capture bar, never on an ordinary refresh. Before investigating anything under this step, confirm: "This also archives or trims docs whose reasoning the codebase already states elsewhere. Proceed, or run the accuracy-only refresh instead?" Decline or silence means skip this step; Step 3's classification is the whole run.

For each doc Step 3 classified **Keep**, apply the counterfactual gate in `ia-compound-docs`: for every claim the doc makes, does a named in-repo artifact (the final code, a test assertion, a code comment, `CLAUDE.md`/`AGENTS.md`, a skill reference, or another surviving doc) state that same reasoning in its own text? Do not infer coverage from a related file name or topic; quote the artifact and the line for each claim checked.

- **Every claim recoverable:** reclassify **Archive**; the quoted artifacts are the report's evidence.
- **Some claims recoverable:** reclassify **Update**; cut the recoverable content, keep what no other artifact states, and point at the artifact in one line where a reader would otherwise look for the cut material.
- **Nothing recoverable:** leave as **Keep**.

Every worth-based Archive or Update still goes through the Step 5 confirmation before anything is applied.

### 4. Report

Present findings as a table:

```
| File | Status | Issue |
|------|--------|-------|
| performance-issues/n-plus-one.md | Keep | All refs valid |
| auth/session-token-bug.md | Update | `auth.js` renamed to `auth.ts` |
| billing/stripe-webhook.md | Archive | Billing module removed in v3 |
| ops/retry-backoff-policy.md | Keep | Code drift: `RetryPolicy` no longer applies jitter the doc mandates -- flag as potential regression |
```

### 4b. Inbound-link check (Archive candidates only)

Before classifying a doc as **Archive**, search the repo's markdown content for citations. A learning that other artifacts cite may carry content the citing docs depend on, even when the doc itself does not say so.

Search both the basename and the path-relative-to-`docs/solutions/` to catch path-qualified citations and avoid false-matching unrelated docs that share a basename across subdirectories:

```bash
rel="${file#docs/solutions/}"          # e.g. "performance-issues/n-plus-one.md"
slug="$(basename "$file" .md)"          # e.g. "n-plus-one"
grep -rn --include='*.md' -e "$rel" -e "$slug" . 2>/dev/null \
  | grep -v "^./$file:"                 # exclude self-references
```

Scope the grep to the repo root, not just `docs/`, so plans, READMEs, AGENTS.md, and other tracked markdown surfaces are checked.

Classify each citation:

- **Decorative**: bare "see also" pointer, attribution, or principle stated inline at the citing site. Archive is fine; clean up the citations in the same pass.
- **Substantive**: the citing doc relies on the cited doc to provide content not stated inline ("see X for the full procedure" with no inline procedure). Downgrade to **Replace** (rewrite at the same path with the current approach) or **Update** (narrow scope to what's still useful).
- **Mixed or unclear**: surface the citations to the user and ask before archiving.

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
- **Archive**: `mkdir -p docs/solutions/_archive && mv [file] docs/solutions/_archive/`, then apply any Cross-file edits from Step 4c (drop decorative citations, repoint substantive citations to the successor doc).

## Constraints

- Never delete learning docs; archive them
- Preserve YAML frontmatter structure when updating
- Don't rewrite docs that are still accurate just to "improve" them
- The Step 3b worth lens is the one exception, and only when the user opted into it: an accurate doc may be archived or trimmed there when its claims are fully recoverable from a quoted in-repo artifact
