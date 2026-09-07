---
name: diagnose-negatives
description: Investigate negative session feedback for a Whetstone skill when asked to diagnose its failures.
---

# diagnose-negatives

Read the [Codex adaptation](../claude-command-compatibility.md), then read the complete [maintained workflow](../../../.claude/commands/diagnose-negatives.md) before acting. Apply that workflow to the current request with its scope and approval boundaries intact.

Use the text following `$diagnose-negatives` as the workflow's `$ARGUMENTS`. When selected from a natural-language request, derive arguments only from the user's stated scope; apply the workflow's missing-argument behavior for anything unspecified.
