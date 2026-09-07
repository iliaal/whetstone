---
name: prune-sync-log
description: Prune stale Whetstone sync decision entries when asked to clean the sync log.
---

# prune-sync-log

Read the [Codex adaptation](../claude-command-compatibility.md), then read the complete [maintained workflow](../../../.claude/commands/prune-sync-log.md) before acting. Apply that workflow to the current request with its scope and approval boundaries intact.

Use the text following `$prune-sync-log` as the workflow's `$ARGUMENTS`. When selected from a natural-language request, derive arguments only from the user's stated scope; apply the workflow's missing-argument behavior for anything unspecified.
