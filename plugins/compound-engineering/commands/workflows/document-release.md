---
name: workflows:document-release
description: Post-ship documentation sync. Reads all project docs, cross-references the diff, updates README/ARCHITECTURE/CONTRIBUTING/CLAUDE.md to match what shipped, polishes CHANGELOG voice, and optionally bumps the version.
argument-hint: "[optional: base branch name]"
---

# Document Release

Run **after code is committed and a PR exists** (or is about to). Cross-reference every documentation file against the diff and bring them up to date.

## Automation rules

Make obvious factual updates directly. Stop and ask only for risky or subjective decisions.

**Never stop for:**
- Factual corrections clearly implied by the diff
- Adding items to tables or lists
- Updating file paths, counts, version numbers
- Fixing stale cross-references
- Minor CHANGELOG wording adjustments
- Marking completed TODO items
- Cross-doc factual inconsistencies (e.g., mismatched version numbers)

**Always stop for:**
- Narrative or philosophical changes to any document
- Removing entire sections
- Security model descriptions
- Large rewrites (more than ~10 lines in one section)
- Ambiguous relevance — changes that might apply but aren't certain

**Hard constraints:**
- Never clobber CHANGELOG entries — polish wording only, preserve all content
- Never use `Write` on CHANGELOG.md — always use `Edit` with exact `old_string` matches
- Never bump VERSION without asking first
- Read the full file before editing any file

---

## Step 0: Detect base branch

Determine the target branch for this PR. Use this as "the base branch" in all subsequent git commands.

```bash
gh pr view --json baseRefName -q .baseRefName 2>/dev/null || \
gh repo view --json defaultBranchRef -q .defaultBranchRef.name 2>/dev/null || \
echo "main"
```

If on the base branch: abort with "You're on the base branch. Run this from a feature branch."

---

## Step 1: Pre-flight & diff analysis

```bash
git diff <base>...HEAD --stat
git log <base>..HEAD --oneline
git diff <base>...HEAD --name-only
```

Discover all documentation files:

```bash
find . -maxdepth 3 -name "*.md" \
  -not -path "./.git/*" \
  -not -path "./node_modules/*" \
  -not -path "./.plan/*" \
  -not -path "./docs/plans/*" \
  -not -path "./docs/brainstorms/*" | sort
```

Classify the diff into categories:
- **New features** — new files, commands, skills, capabilities
- **Changed behavior** — modified APIs, config, existing functionality
- **Removed functionality** — deleted files or commands
- **Infrastructure** — build, test, CI changes

Output: "Analyzing N files changed across M commits. Found K documentation files to review."

---

## Step 2: Per-file documentation audit

Read each documentation file and cross-reference against the diff. Classify each needed change as **auto-update** (factual, clearly warranted) or **ask user** (narrative, ambiguous, large).

**README.md:**
- Does it describe all features and capabilities visible in the diff?
- Are install/setup instructions consistent with the changes?
- Are examples, usage descriptions, and tables still valid?

**ARCHITECTURE.md:**
- Do component descriptions and diagrams match the current code?
- Are design decision explanations still accurate?
- Be conservative — only update what the diff clearly contradicts.

**CONTRIBUTING.md:**
- Walk through the setup instructions as a new contributor would.
- Would each listed command succeed today?
- Do test tier descriptions match current test infrastructure?

**CLAUDE.md / AGENTS.md:**
- Does the project structure section match the actual file tree?
- Are listed commands, scripts, and file paths accurate?
- Do build/test instructions match what's in the package manager config?

**Any other .md files:**
- Read the file, determine its purpose and audience.
- Check whether the diff contradicts anything it says.

---

## Step 3: Apply auto-updates

Make all clear, factual updates using the Edit tool.

For each file modified, output a one-line summary of **what specifically changed** — not "Updated README.md" but "README.md: added document-release to commands table, updated count from 19 to 20."

**Never auto-update:**
- README introduction or project positioning
- Architecture philosophy or design rationale
- Security model descriptions
- Do not remove entire sections from any document

---

## Step 4: Ask about risky changes

For each risky or ambiguous update identified in Step 2, ask the user with:
- Which file and what specific change is being considered
- A clear recommendation with reasoning
- Options including "Skip — leave as-is"

Apply approved changes immediately after each answer.

---

## Step 5: CHANGELOG voice polish

**Only run if CHANGELOG was modified on this branch.**

**CRITICAL — never clobber CHANGELOG entries.** Polish wording only. Never delete, reorder, or replace entries. The entry content is the source of truth — you are polishing prose, not rewriting history. Use `Edit` with exact `old_string` matches; never `Write`.

Review the modified entries for voice. Apply the writing skill principles:
- Lead with what the user can now **do**, not implementation details
- "Added X" over "Refactored the X system to support..."
- Cut hedging, vague declaratives, and throat-clearing
- Internal/contributor-only changes belong in a separate `### For contributors` subsection
- Auto-fix minor wording. Ask if a rewrite would alter meaning.

---

## Step 6: Cross-doc consistency check

After auditing files individually, do a cross-doc pass:

1. Does the README feature list match what CLAUDE.md/AGENTS.md describes?
2. Does ARCHITECTURE's component list match CONTRIBUTING's project structure?
3. Does the CHANGELOG's latest version match the VERSION file or `version` field in the package manifest?
4. **Discoverability:** Is every documentation file reachable from README.md or CLAUDE.md/AGENTS.md? If ARCHITECTURE.md exists but neither entry-point file links to it, flag it.

Auto-fix clear factual inconsistencies. Ask for narrative contradictions.

---

## Step 7: TODOS cleanup

Skip if TODOS.md does not exist.

1. **Completed items not yet marked:** Cross-reference the diff against open TODO items. If a TODO is clearly completed by changes in this branch, move it to the Completed section with `**Completed:** vX.Y.Z (YYYY-MM-DD)`. Be conservative — clear evidence in the diff only.

2. **New deferred work:** Check the diff for `TODO`, `FIXME`, `HACK`, and `XXX` comments. For each one representing meaningful deferred work (not trivial inline notes), ask whether it should be captured in TODOS.md.

---

## Step 8: VERSION bump

**Never bump VERSION without asking.**

Check if VERSION (or the version field in plugin.json/package.json/pyproject.toml) was already modified on this branch:

```bash
git diff <base>...HEAD -- VERSION plugin.json package.json pyproject.toml 2>/dev/null
```

**If not bumped:** Ask:
- A) Bump PATCH — if doc changes accompany code changes
- B) Bump MINOR — if this is a significant standalone release
- C) Skip — no bump needed
- Recommend C for docs-only branches

**If already bumped:** Verify the bump covers the full scope of changes on this branch. If there are significant changes not mentioned in the corresponding CHANGELOG entry, ask whether to bump again or add to the existing entry.

---

## Step 9: Commit & output

**Empty check first:**

```bash
git status
```

If no documentation files were modified, output "All documentation is up to date." and exit without committing.

**Stage and commit modified documentation files by name:**

```bash
git add <file1> <file2> ...
git commit -m "docs: sync documentation for vX.Y.Z"
git push
```

**PR body update:**

```bash
# Read existing PR body
gh pr view --json body -q .body > /tmp/doc-release-$$.md

# Append or replace a ## Documentation section with a per-file change summary
# Then write back:
gh pr edit --body-file /tmp/doc-release-$$.md
rm -f /tmp/doc-release-$$.md
```

If no PR exists: skip with "No PR found — documentation changes are in the commit."
If `gh pr edit` fails: warn and continue.

**Documentation health summary (final output):**

```
Documentation health:
  README.md       [Updated — added X to table, count 19→20]
  ARCHITECTURE.md [Current — no changes needed]
  CONTRIBUTING.md [Updated — fixed setup command]
  CHANGELOG.md    [Voice polished — 2 entries]
  AGENTS.md       [Current]
  VERSION         [Bumped — 2.45.5 → 2.45.6]
```

Status values: `Updated`, `Current`, `Voice polished`, `Skipped (not found)`, `Not bumped — user chose to skip`
