---
name: write-skill
description: Author a new Whetstone plugin skill when asked to write a skill without upstream skills.sh sources.
---

# write-skill

Read the [Codex adaptation](../claude-command-compatibility.md), then read the complete [maintained workflow](../../../.claude/commands/write-skill.md) before acting. Apply that workflow to the current request with its scope and approval boundaries intact.

Use the text following `$write-skill` as the workflow's `$ARGUMENTS`. When selected from a natural-language request, derive arguments only from the user's stated scope; apply the workflow's missing-argument behavior for anything unspecified.
