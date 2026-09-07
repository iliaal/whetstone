---
name: eval-skills
description: Evaluate Whetstone skills from session evidence when asked to compare procedure-following results or optimization candidates.
---

# eval-skills

Read the [Codex adaptation](../claude-command-compatibility.md), then read the complete [maintained workflow](../../../.claude/commands/eval-skills.md) before acting. Apply that workflow to the current request with its scope and approval boundaries intact.

Use the text following `$eval-skills` as the workflow's `$ARGUMENTS`. When selected from a natural-language request, derive arguments only from the user's stated scope; apply the workflow's missing-argument behavior for anything unspecified.
