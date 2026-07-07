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
2. Get judge tasks: `python3 distillery/scripts/distiller.py scan-injection --emit-tasks --changed-since "$prev_tag"`. Returns `{count, tasks:[{file, prompt, ...}]}`. **`count` is the number of TASKS, not files:** large files are split into full-coverage chunks and emit one task per chunk (multi-chunk tasks carry `chunk` and `chunks_total` fields), so `count` can exceed the changed-file count. If `count` is 0, skip to Phase 4 — nothing changed to judge.
3. Pick a fresh per-run verdicts file so a stale file from a prior run can never be reused: `verdicts_file=$(mktemp /tmp/injection-verdicts.XXXXXX.json)`. For each task, spawn a sub-agent (Agent tool, `general-purpose`) whose **entire instruction is the task's `prompt`** (the file content is already embedded in it — the agent reads nothing). Fan out in parallel, batched ~8 per message. Each sub-agent returns ONLY a JSON verdict: `{verdict, confidence, categories, evidence, rationale}`.
4. From each sub-agent's reply, extract the JSON verdict object (an agent may wrap it in prose — take the `{...}` containing `"verdict"`). Assemble a JSON array of `{file, verdict, confidence, categories, evidence, rationale}` — **one entry per TASK** (carry each task's `file`, and its `chunk`/`chunks_total` if present) — and write it to `$verdicts_file`. **The verdict count MUST equal the task `count` from step 2, not the file count** (a multi-chunk file needs one verdict per chunk). If an agent returned no parseable verdict, re-dispatch that one task before continuing. Multi-chunk verdicts collapse to one worst-per-file verdict inside the attestation writer.
5. If ANY verdict is `malicious`: **STOP the release.** Report the file, evidence, and rationale. Do not write the attestation, do not run Phase 4.
6. Otherwise write the attestation: `python3 distillery/scripts/distiller.py scan-injection --write-attestation --changed-since "$prev_tag" --verdicts @"$verdicts_file"`. Surface any `suspicious` verdicts to the user as a heads-up; they do not block.
7. Proceed to Phase 4.

The attestation is bound to the changed files' content hash. If any of those files are edited after this phase, `release.sh` rejects the now-stale attestation and you must re-run Phase 3.5.

## Phase 4: Ship

Run `bash scripts/release.sh "$ARGUMENTS"` — this handles:

- Version consistency check (plugin.json vs marketplace.json)
- **Pre-commit gates** (each with its blocking status):
  - `update-metadata.sh --check` — **BLOCKING**. Aborts if component counts / descriptions drifted from plugin.json + marketplace.json.
  - Trigger regression tests (`test-triggers`) — **BLOCKING**. Aborts on any failing trigger fixture.
  - Tier-1 prompt-injection corpus scan (`scan-injection`, deterministic) — **BLOCKING on HIGH**. Aborts if any HIGH-severity finding.
  - Tier-2 attestation verify (`scan-injection --verify-attestation`) — **BLOCKING**; verifies the Phase 3.5 sub-agent judge pass produced a valid content-bound attestation for the changed-file set. **Skipped with a WARNING** (non-blocking) when no previous `v*` tag exists.
  - Skill-injection hook tests (`test-semantic`) — **NON-BLOCKING**. Prints a WARNING on failure and continues. (These are deterministic hook-firing tests, distinct from the Tier-1/Tier-2 prompt-injection scan above.)
  - Skill manifest regeneration (`generate-manifest.py`) — the baseline is first reset to the last-released manifest (from the `v*` tag) so mid-work regens can't freeze changed skills at the old version and make ClawHub false-skip them.
- Commit all plugin changes + CHANGELOG + marketplace.json, push to `origin/master`
- Sync the GitHub repo description from `plugin.json`
- **Create the GitHub release on whetstone** — this mints the `v<version>` tag. Phase 1's `git log v<current>..HEAD` on the *next* release depends on this tag existing, so a skipped/failed GitHub release silently breaks the next changelog survey.
- Mirror skills to `~/ai/ai-skills`, **sync the ai-skills CHANGELOG** (extract skill-related entries from this release's notes), push, and **create the ai-skills GitHub release**
- Publish skills to the ClawHub registry via `publish-clawhub.sh` — **non-fatal** (see below)
- Sync skills to other tools (Codex, Kilocode) via `sync-to-tools.sh`
- Update the locally installed plugin via `update-plugin.sh`
- `git fetch --tags` back-sync so local tags match the remote release tag just minted

**ClawHub partial-failure behavior.** The publish step is non-fatal, so a release can complete (commit, push, mirror, local sync all done) while ClawHub is left un-updated in two cases:

- **Unauthenticated** (`clawhub whoami` fails): publish is skipped with a WARNING.
- **Publish error** (`publish-clawhub.sh` exits non-zero): the step logs a WARNING and continues; the remaining local steps still run.

In both cases `release.sh` prints a prominent `ACTION REQUIRED` block at the end naming the cause and the exact resume command. Resume path: `npx clawhub@latest login` (only if unauthenticated) then `bash scripts/publish-clawhub.sh`. `publish-clawhub.sh` skips versions already on the registry, so re-running it is safe.

If `$ARGUMENTS` is empty, `release.sh` auto-generates the commit message from the CHANGELOG headline.

## Phase 5: Report

State the version that shipped and the commit count that was bundled into it.

## Constraints

- Do not bump the version or touch CHANGELOG.md outside this command. Per-change ceremony is explicitly forbidden by `CLAUDE.md`.
- Do not skip the pre-flight survey — blindly bumping without reading `git log` produces inaccurate CHANGELOGs.
- If the working tree is clean and `git log v<current>..HEAD` is empty, stop — there is nothing to release.
- Never force-push to `master`.
