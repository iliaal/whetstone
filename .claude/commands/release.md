---
name: release
description: Bump version, commit, push, mirror to ai-skills, and update local plugin
argument-hint: "[optional: commit message]"
---

# Release

Run the full release pipeline for the compound-engineering plugin.

## Steps

1. Run `bash scripts/update-metadata.sh` to ensure counts are current
2. Validate JSON: `jq . .claude-plugin/marketplace.json && jq . plugins/compound-engineering/.claude-plugin/plugin.json`
3. Run `bash scripts/release.sh "$ARGUMENTS"` — this handles:
   - Version consistency check (plugin.json vs marketplace.json)
   - Commit all plugin changes + CHANGELOG + marketplace.json
   - Push to origin/main
   - Mirror skills to ~/ai/ai-skills and push
   - Sync skills to other tools (Codex, Kilocode) via sync-to-tools.sh
   - Update locally installed plugin via update-plugin.sh
4. Report the version that was released

If `$ARGUMENTS` is empty, the release script auto-generates a commit message from the CHANGELOG.

**Pre-flight check:** Before running, verify there are actual changes to commit (`git status`). If the working tree is clean, stop and say so.
