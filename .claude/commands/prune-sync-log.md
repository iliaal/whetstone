---
name: prune-sync-log
description: Prune stale entries from the whetstone sync decision log
---

# Prune sync log

Archive entries in `docs/audit/audit-log.md` that are no longer load-bearing, so the pre-flight filter in `/sync-from-repos` and `/audit-plugin` stays lean and current.

## Configuration

```
SYNC_LOG=docs/audit/audit-log.md
ARCHIVE=docs/audit/audit-log-archive.md
PLUGIN_DIR=plugins/whetstone
REPOS_DIR=~/ai/repos
TODAY=YYYY-MM-DD  # resolve to actual date at run time
```

## Phase 1: Inventory

Read `$SYNC_LOG` in full. Parse it into run entries keyed by `(date, type, scope)`. For each entry, extract every bullet under Applied / Rejected / Deferred along with the component it targets.

If the file doesn't exist, report that and stop.

## Phase 2: Classify each entry

For every run entry, assign one of four statuses. Classification happens at the entry level (whole run), not per bullet, because entries are the unit of append.

| Status | Criteria | Action |
|--------|----------|--------|
| **Keep** | Entry <30 days old AND every referenced component still exists AND reasoning not superseded AND referenced repos still in `$REPOS_DIR` | Leave in place |
| **Prune — age** | Entry >30 days old and no longer load-bearing for current plugin state | Move to archive |
| **Prune — stale-ref** | One or more bullets reference a component path that no longer exists under `$PLUGIN_DIR`, OR an external repo no longer in `$REPOS_DIR` | Move to archive (even if <30 days — stale refs confuse the filter) |
| **Prune — superseded** | Reasoning for a rejection has been promoted to a feedback-memory rule in `MEMORY.md`, or a later entry applies the same change and overrides the rejection | Move to archive |

Stale-ref detection: for each bullet, resolve the backtick-quoted component name to a path under `$PLUGIN_DIR` (skills/agents/commands). Use Glob or Grep to confirm existence. If the entry references an external repo by name (e.g., "Source repo: gstack"), check for `$REPOS_DIR/gstack/`.

Supersession detection: read `~/.claude/projects/-home-ilia-ai-whetstone/memory/MEMORY.md` and scan feedback entries. If a rejection reason in a log bullet matches the rule in a feedback entry (same pattern, same target), mark the bullet as superseded. When more than half of an entry's bullets are superseded, prune the entry.

## Phase 3: Report

Present a single table sorted by status severity (stale-ref first, then superseded, then age, then keep):

```
| Date       | Type  | Scope       | Status          | Reason                                           |
|------------|-------|-------------|-----------------|--------------------------------------------------|
| 2026-02-10 | sync  | postgresql  | Prune stale-ref | references deleted `legacy-db-helpers` skill     |
| 2026-02-22 | audit | full        | Prune age       | 49 days old, no longer matches current state     |
| 2026-03-15 | sync  | code-review | Prune superseded| rejection reason covered by feedback_code_review |
| 2026-04-01 | sync  | writing     | Keep            | 10 days old, all refs valid                      |
```

Include a summary line: "Prune candidates: N age, M stale-ref, K superseded. X entries kept."

## Phase 4: Apply

Ask: "Archive these entries? (all / pick by date / skip)"

For approved entries:

1. **Create archive file** if `$ARCHIVE` doesn't exist. Header template:

   ```markdown
   # Compound Engineering Sync Log — Archive

   Pruned entries from `whetstone-sync-log.md`. Each entry retains its original heading and body, with a prune footer noting the date and reason.
   ```

2. **Move each approved entry** to `$ARCHIVE`. Append under the `# Compound Engineering Sync Log — Archive` heading (archive is not ordered, just a dumping ground for history).

3. **Append a prune footer** to each archived entry:

   ```markdown
   > Pruned YYYY-MM-DD — reason: age | stale-ref (`component-name`) | superseded (`feedback_file.md`)
   ```

4. **Remove the entry** from `$SYNC_LOG` using Edit. Do not leave a placeholder or a "see archive" comment — the whole point is to shrink the live log.

## Phase 5: Verify

Run these checks:

- `$SYNC_LOG` still parses: headings intact, Log marker present, no orphaned bullets.
- `$ARCHIVE` contains exactly the pruned entries with prune footers.
- Entry count in live log matches `original - pruned`.
- No entry appears in both files (moved, not copied).

Report: "Pruned N entries. Live log now has M entries. Archive has K total."

## Constraints

- Never delete entries without archiving — history is the point.
- Never prune an entry younger than 30 days unless it has a stale reference.
- Never prune without user approval.
- If the live log is empty after pruning, leave the file structure (header + template + empty Log section) intact.
- Do not rewrite or reformat entries during the move — preserve original wording so the archive remains a faithful record.
