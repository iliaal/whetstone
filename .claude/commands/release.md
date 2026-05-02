---
name: release
description: Bump version, commit, push, mirror to ai-skills, and update local plugin
argument-hint: "[optional: commit message]"
---

# Release

Run the full release pipeline for the whetstone plugin. This command owns all version ceremony — per-change edits do NOT bump versions or touch CHANGELOG.md. Those steps happen here, once, summarizing everything that accumulated since the last release.

## Phase 1: Survey what changed since the last release

1. Find the current version in `plugins/whetstone/.claude-plugin/plugin.json`.
2. Run `git log v<current-version>..HEAD --oneline` (fallback: `git log --since="<last release date>" --oneline`) to list commits since the last tag.
3. Run `git diff v<current-version>..HEAD --stat` to see which files changed.
4. Classify the changes into added/changed/fixed/removed buckets per Keep a Changelog. Scan specifically for:
   - New files under `plugins/whetstone/{skills,agents,commands}/` → Added
   - Deletions under the same paths → Removed
   - Edits to existing components → Changed
   - Commits with `fix:` prefix or bug-fix language → Fixed

## Phase 2: Decide the semver bump

- **MAJOR** if any breaking change (component removed, renamed, frontmatter contract changed)
- **MINOR** if any new skill, agent, or command was added
- **PATCH** otherwise (edits, doc updates, trigger-pattern tweaks)

Ask the user to confirm the bump type before writing anything, and offer a short rationale.

## Phase 3: Apply the bump

1. Update `version` field in both `plugins/whetstone/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`. Both must match.
2. Prepend a new CHANGELOG.md entry with today's date, the new version, a one-line summary, and buckets of commits grouped under `### Added` / `### Changed` / `### Fixed` / `### Removed`. Use the writing skill to polish the tone before committing.
3. Run `bash scripts/update-metadata.sh` to sync component counts into plugin.json and marketplace.json descriptions.
4. Verify README.md agent/command/skill counts and tables still match reality — update if drift.
5. Validate JSON: `jq . .claude-plugin/marketplace.json && jq . plugins/whetstone/.claude-plugin/plugin.json`.

## Phase 4: Ship

Run `bash scripts/release.sh "$ARGUMENTS"` — this handles:

- Version consistency check (plugin.json vs marketplace.json)
- Pre-commit gates: trigger regression tests, semantic injection tests, skill manifest regeneration
- Commit all plugin changes + CHANGELOG + marketplace.json
- Push to `origin/main`
- Mirror skills to `~/ai/ai-skills` and push
- Publish skills to the ClawHub registry via `publish-clawhub.sh`
- Sync skills to other tools (Codex, Kilocode) via `sync-to-tools.sh`
- Update the locally installed plugin via `update-plugin.sh`

If `$ARGUMENTS` is empty, `release.sh` auto-generates the commit message from the CHANGELOG headline.

## Phase 5: Report

State the version that shipped and the commit count that was bundled into it.

## Constraints

- Do not bump the version or touch CHANGELOG.md outside this command. Per-change ceremony is explicitly forbidden by `CLAUDE.md`.
- Do not skip the pre-flight survey — blindly bumping without reading `git log` produces inaccurate CHANGELOGs.
- If the working tree is clean and `git log v<current>..HEAD` is empty, stop — there is nothing to release.
- Never force-push to `main`.
