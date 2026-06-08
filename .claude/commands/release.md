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

## Phase 3.5: Tier-2 prompt-injection judge (sub-agents)

Semantic injection screening of every `.md` file changed since the last release, run as **parallel sub-agents** (not `claude -p`). This writes the content-bound attestation that Phase 4's `release.sh` verifies — `release.sh` will refuse to ship without it.

1. Prior release ref: `prev_tag=$(git describe --tags --abbrev=0 --match 'v*')`.
2. Get judge tasks: `python3 distillery/scripts/distiller.py scan-injection --emit-tasks --changed-since "$prev_tag"`. Returns `{count, tasks:[{file, prompt}]}`. If `count` is 0, skip to Phase 4 — nothing changed to judge.
3. For each task, spawn a sub-agent (Agent tool, `general-purpose`) whose **entire instruction is the task's `prompt`** (the file content is already embedded in it — the agent reads nothing). Fan out in parallel, batched ~8 per message. Each sub-agent returns ONLY a JSON verdict: `{verdict, confidence, categories, evidence, rationale}`.
4. From each sub-agent's reply, extract the JSON verdict object (an agent may wrap it in prose — take the `{...}` containing `"verdict"`). Assemble a JSON array of `{file, verdict, confidence, categories, evidence, rationale}` (one per task, carrying the task's `file`) and write it to `/tmp/injection-verdicts.json`. If an agent returned no parseable verdict, re-dispatch that one task before continuing.
5. If ANY verdict is `malicious`: **STOP the release.** Report the file, evidence, and rationale. Do not write the attestation, do not run Phase 4.
6. Otherwise write the attestation: `python3 distillery/scripts/distiller.py scan-injection --write-attestation --changed-since "$prev_tag" --verdicts @/tmp/injection-verdicts.json`. Surface any `suspicious` verdicts to the user as a heads-up; they do not block.
7. Proceed to Phase 4.

The attestation is bound to the changed files' content hash. If any of those files are edited after this phase, `release.sh` rejects the now-stale attestation and you must re-run Phase 3.5.

## Phase 4: Ship

Run `bash scripts/release.sh "$ARGUMENTS"` — this handles:

- Version consistency check (plugin.json vs marketplace.json)
- Pre-commit gates: trigger regression tests, prompt-injection corpus scan (Tier-1 deterministic, fails on HIGH), Tier-2 attestation check (verifies the Phase 3.5 sub-agent judge pass ran clean on the changed files; fails if no valid content-bound attestation exists), semantic injection tests, skill manifest regeneration
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
