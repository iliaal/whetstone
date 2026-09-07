---
name: release
description: Run the Whetstone release workflow when explicitly asked to release this plugin.
---

# release

Read the [Codex adaptation](../claude-command-compatibility.md), then read the complete [maintained workflow](../../../.claude/commands/release.md) before acting. Apply that workflow to the current request with its scope and approval boundaries intact.

Use the text following `$release` as the workflow's `$ARGUMENTS`. When selected from a natural-language request, derive arguments only from the user's stated scope; apply the workflow's missing-argument behavior for anything unspecified.
