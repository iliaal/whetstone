---
name: analyze-misfires
description: Analyze Whetstone skill injection misfires when asked to investigate overly broad triggers or irrelevant injected skills.
---

# analyze-misfires

Read the [Codex adaptation](../claude-command-compatibility.md), then read the complete [maintained workflow](../../../.claude/commands/analyze-misfires.md) before acting. Apply that workflow to the current request with its scope and approval boundaries intact.

Use the text following `$analyze-misfires` as the workflow's `$ARGUMENTS`. When selected from a natural-language request, derive arguments only from the user's stated scope; apply the workflow's missing-argument behavior for anything unspecified.
