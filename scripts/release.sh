#!/usr/bin/env bash
# Release pipeline: commit, refresh local Codex, push, mirror, update local Claude
# Usage: bash scripts/release.sh ["commit message"]
#   If no message provided, auto-generates from version + CHANGELOG headline
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
AI_SKILLS_DIR="$HOME/ai/ai-skills"
RELEASE_BRANCH="master"
# Pinned so a compromised or breaking clawhub release cannot run with the
# registry token. Keep in sync with CLAWHUB_VERSION in publish-clawhub.sh.
CLAWHUB_VERSION="0.23.3"
CLAWHUB_CLI=(npx --yes "clawhub@${CLAWHUB_VERSION}")

# Abort unless the repo at $1 has RELEASE_BRANCH checked out, no merge or
# cherry-pick in progress, and already contains origin/RELEASE_BRANCH, so the
# release commit lands on top of origin as a fast-forward.
require_release_branch() {
	local dir="$1" label="$2" branch
	if ! git -C "$dir" rev-parse --git-dir >/dev/null 2>&1; then
		echo "ERROR: $label ($dir) is not a git repository."
		exit 1
	fi
	branch=$(git -C "$dir" symbolic-ref --quiet --short HEAD 2>/dev/null || true)
	if [[ "$branch" != "$RELEASE_BRANCH" ]]; then
		echo "ERROR: $label is on '${branch:-detached HEAD}', not '$RELEASE_BRANCH'. Releases run only from $RELEASE_BRANCH."
		exit 1
	fi
	if git -C "$dir" rev-parse -q --verify MERGE_HEAD >/dev/null || git -C "$dir" rev-parse -q --verify CHERRY_PICK_HEAD >/dev/null; then
		echo "ERROR: $label has a merge or cherry-pick in progress."
		exit 1
	fi
	git -C "$dir" fetch --quiet origin "$RELEASE_BRANCH" || {
		echo "ERROR: Could not fetch origin/$RELEASE_BRANCH for $label."
		exit 1
	}
	if ! git -C "$dir" merge-base --is-ancestor FETCH_HEAD HEAD; then
		echo "ERROR: $label $RELEASE_BRANCH is behind or diverged from origin/$RELEASE_BRANCH. Integrate origin first."
		exit 1
	fi
}

# Push the commit by SHA, not by branch name: `git push origin master` publishes
# whatever local master holds, which need not be the commit just created. The
# ls-remote check gates tagging, mirroring, and publication on the remote ref.
push_release_sha() {
	local dir="$1" label="$2" sha="$3" remote_sha
	git -C "$dir" push origin "${sha}:refs/heads/${RELEASE_BRANCH}"
	remote_sha=$(git -C "$dir" ls-remote origin "refs/heads/${RELEASE_BRANCH}" | awk '{print $1}')
	if [[ "$remote_sha" != "$sha" ]]; then
		echo "ERROR: $label origin/$RELEASE_BRANCH is '${remote_sha:-missing}', expected release commit $sha. Stopping before tagging or publication."
		exit 1
	fi
}

# --- Preflight ---
cd "$ROOT_DIR"

require_release_branch "$ROOT_DIR" "whetstone"
require_release_branch "$AI_SKILLS_DIR" "ai-skills"
if [[ -n "$(git -C "$AI_SKILLS_DIR" status --porcelain)" ]]; then
	echo "ERROR: ai-skills working tree is not clean; the release commits everything there with 'git add -A'."
	git -C "$AI_SKILLS_DIR" status --short
	exit 1
fi

version=$(python3 -c "import json; print(json.load(open('plugins/whetstone/.claude-plugin/plugin.json'))['version'])")
codex_version=$(python3 -c "import json; print(json.load(open('plugins/whetstone/.codex-plugin/plugin.json'))['version'])")
marketplace_version=$(python3 -c "import json; print(json.load(open('.claude-plugin/marketplace.json'))['plugins'][0]['version'])")

if [[ "$version" == "$marketplace_version" && "$version" == "$codex_version" ]]; then
	:
else
	echo "ERROR: Version mismatch — Claude plugin ($version), Claude marketplace ($marketplace_version), Codex plugin ($codex_version)"
	exit 1
fi

# Check JSON validity
jq . .claude-plugin/marketplace.json >/dev/null || {
	echo "ERROR: marketplace.json is invalid JSON"
	exit 1
}
jq . plugins/whetstone/.claude-plugin/plugin.json >/dev/null || {
	echo "ERROR: plugin.json is invalid JSON"
	exit 1
}
jq . .agents/plugins/marketplace.json >/dev/null || {
	echo "ERROR: Codex marketplace.json is invalid JSON"
	exit 1
}
jq . plugins/whetstone/.codex-plugin/plugin.json >/dev/null || {
	echo "ERROR: Codex plugin.json is invalid JSON"
	exit 1
}
jq . plugins/whetstone/.mcp.json >/dev/null || {
	echo "ERROR: Codex .mcp.json is invalid JSON"
	exit 1
}

# --- Pre-commit gates ---
echo "[Pre-commit] Checking metadata is in sync with component counts..."
bash "$SCRIPT_DIR/update-metadata.sh" --check || {
	echo "ERROR: plugin.json / marketplace.json metadata is stale. Run 'bash scripts/update-metadata.sh' and commit the result."
	exit 1
}
echo "  Metadata in sync"

echo "[Pre-commit] Validating plugin components..."
python3 distillery/scripts/distiller.py validate-plugin >/dev/null || {
	echo "ERROR: validate-plugin found HIGH-severity findings."
	echo "       Run 'python3 distillery/scripts/distiller.py validate-plugin' to see them."
	exit 1
}
echo "  Plugin validation passed (no HIGH findings)"

echo "[Pre-commit] Validating cross-references..."
bash "$SCRIPT_DIR/validate-cross-refs.sh" >/dev/null || {
	echo "ERROR: Broken cross-reference(s) found."
	echo "       Run 'bash scripts/validate-cross-refs.sh' to see them."
	exit 1
}
echo "  Cross-references valid"

echo "[Pre-commit] Running native Codex plugin regression tests..."
bash "$SCRIPT_DIR/test-codex-plugin.sh" || {
	echo "ERROR: Native Codex plugin regression tests failed."
	exit 1
}
echo "  Codex plugin regression tests passed"

echo "[Pre-commit] Running release script regression tests..."
bash "$SCRIPT_DIR/test-release-scripts.sh" >/dev/null || {
	echo "ERROR: Release script regression tests failed."
	echo "       Run 'bash scripts/test-release-scripts.sh' to see them."
	exit 1
}
echo "  Release script regression tests passed"

echo "[Pre-commit] Running trigger regression tests..."
python3 distillery/scripts/distiller.py test-triggers >/dev/null || {
	echo "ERROR: Trigger regression tests failed. Fix patterns or fixtures before release."
	exit 1
}
echo "  Trigger tests passed"

echo "[Pre-commit] Scanning corpus for prompt-injection / supply-chain content..."
python3 distillery/scripts/distiller.py scan-injection >/dev/null || {
	echo "ERROR: Prompt-injection scan found HIGH-severity content in the plugin corpus."
	echo "       Run 'python3 distillery/scripts/distiller.py scan-injection' to see findings."
	exit 1
}
echo "  Injection scan passed (no HIGH findings)"

echo "[Pre-commit] Verifying Tier-2 prompt-injection attestation for changed files..."
prev_tag="$(git describe --tags --abbrev=0 --match 'v*' 2>/dev/null || true)"
if [[ -n "$prev_tag" ]]; then
	python3 distillery/scripts/distiller.py scan-injection --verify-attestation --changed-since "$prev_tag" || {
		echo "ERROR: No valid Tier-2 prompt-injection attestation for the current changed-file set."
		echo "       Tier-2 judging runs as a sub-agent pass inside the /release command (Phase 3.5),"
		echo "       which writes the content-bound attestation this gate verifies."
		echo "       Run the release via /release, not 'bash release.sh' directly."
		exit 1
	}
	echo "  Tier-2 attestation valid"
else
	echo "  WARNING: no previous release tag found; skipping Tier-2 attestation check."
fi

echo "[Pre-commit] Running skill-injection hook tests (deterministic, no API cost)..."
if python3 distillery/scripts/distiller.py test-semantic >/dev/null; then
	echo "  Hook tests passed"
else
	echo "  WARNING: skill-injection hook test(s) failed (see above). Non-blocking; review trigger coverage."
fi

echo "[Pre-commit] Generating skill change manifest..."
# Regenerate from the last release tag's manifest. generate-manifest.py keeps
# content_changed when the working-tree manifest already has the new hash, so a
# mid-work regen would freeze changed skills at the old version and
# publish-clawhub.sh would skip them.
last_release_tag="$(git describe --tags --abbrev=0 --match 'v*' 2>/dev/null || true)"
if [[ -n "$last_release_tag" ]]; then
	git show "$last_release_tag:distillery/.skill-versions.json" >distillery/.skill-versions.json 2>/dev/null || true
fi
python3 "$SCRIPT_DIR/generate-manifest.py"
echo "  Manifest updated"

if [[ -z "$(git status --porcelain)" ]]; then
	echo "ERROR: Nothing to commit"
	exit 1
fi

# Auto-generate commit message from CHANGELOG if not provided
if [[ -n "${1:-}" ]]; then
	commit_msg="$1"
else
	changelog_headline=$(sed -n "/^## \[${version}\]/,/^## \[/{/^## \[${version}\]/d;/^## \[/d;/^$/d;/^###/{ s/^### //; p; q; }}" CHANGELOG.md 2>/dev/null)
	if [[ -n "$changelog_headline" ]]; then
		commit_msg="bump: v${version} — $(echo "$changelog_headline" | tr '[:upper:]' '[:lower:]')"
	else
		commit_msg="bump: v${version}"
	fi
	echo "Commit message: $commit_msg"
fi

echo "=== Release v${version} ==="
echo ""

# --- 1. Commit & Push ---
echo "[1/9] Commit, refresh Codex & push..."
git add -A -- \
	.agents/plugins/marketplace.json \
	.claude-plugin/marketplace.json \
	AGENTS.md \
	CHANGELOG.md \
	README.md \
	distillery/.skill-versions.json \
	distillery/scripts/ \
	distillery/tests/ \
	scripts/ \
	plugins/whetstone/
# Also stage project-level skill and command changes if any
git add -A -- .claude/skills/ 2>/dev/null || true
git add -A -- .claude/commands/ 2>/dev/null || true
git commit -m "$commit_msg"
release_sha=$(git rev-parse HEAD)

if command -v codex >/dev/null 2>&1; then
	echo "  Refreshing native Codex plugin before publication..."
	# Skip install's own sync-to-tools; step 6 runs it once after push.
	WHETSTONE_SKIP_POST_INSTALL_SYNC=1 bash "$SCRIPT_DIR/install-codex-plugin.sh" || {
		echo "ERROR: Failed to install and activate the local Whetstone Codex plugin. Release commit was not pushed."
		exit 1
	}
	echo "  Codex plugin refreshed; start a new Codex thread to load v${version}"
else
	echo "  No 'codex' on PATH; skipping native Codex plugin refresh."
fi

push_release_sha "$ROOT_DIR" "whetstone" "$release_sha"
echo "  Pushed $release_sha to origin/$RELEASE_BRANCH"

# --- 2. Sync GitHub repo description ---
echo "[2/9] Sync repo description..."
repo_desc=$(jq -r '.description' plugins/whetstone/.claude-plugin/plugin.json)
gh repo edit --description "$repo_desc" 2>/dev/null && echo "  Updated repo description" || echo "  Failed to update repo description (non-fatal)"

# --- 3. Create GitHub release on plugin repo ---
echo "[3/9] Create GitHub release..."
release_notes=$(sed -n "/^## \[${version}\]/,/^## \[/{/^## \[${version}\]/d;/^## \[/d;p;}" CHANGELOG.md)
if gh release view "v${version}" &>/dev/null; then
	echo "  Release v${version} already exists, skipping"
else
	gh release create "v${version}" \
		--title "v${version}" \
		--notes "$release_notes" \
		--target "$release_sha"
	echo "  Created release v${version}"
fi

# --- 4. Mirror to ai-skills ---
echo "[4/9] Mirror to ai-skills..."
bash "$SCRIPT_DIR/mirror-to-ai-skills.sh"

# Sync changelog: extract skill-related entries from plugin changelog
echo "  Syncing changelog..."
# Build allowlist from actual skill directories (longest names first to avoid prefix conflicts)
skill_names=$(find "$ROOT_DIR/plugins/whetstone/skills" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | awk '{print length, $0}' | sort -rn | awk '{print $2}' | tr '\n' '|' | sed 's/|$//')
# Keep ### headers and bullets that name a known skill anywhere in the line:
# backticked or bare, with or without the ia- prefix, hyphenated (orchestrating-swarms)
# or spaced (orchestrating swarms). Bullets are prose, so a start-of-line match
# misses most of them. A format change that stops matching trips the WARNING below.
skill_names_spaced=$(printf '%s\n' "$skill_names" | tr '|' '\n' | sed 's/-/ /g' | paste -sd'|')
skill_notes=$(printf '%s\n' "$release_notes" | grep -iE "^### |^- .*(\b(ia-)?(${skill_names})\b|\b(${skill_names_spaced})\b)" || true)
# Strip orphan ### headers (headers with no entries after them)
skill_notes=$(printf '%s\n' "$skill_notes" | awk '/^### /{header=$0; next} /^- /{if(header){print header; header=""} print}')
if [[ -n "$skill_notes" ]]; then
	ai_skills_changelog="$AI_SKILLS_DIR/CHANGELOG.md"
	new_entry="## [${version}] - $(date +%Y-%m-%d)

${skill_notes}"
	# Insert before the first existing version entry.
	first_version_line=$(grep -n '^## \[' "$ai_skills_changelog" | head -1 | cut -d: -f1)
	if [[ -n "$first_version_line" ]]; then
		head -n $((first_version_line - 1)) "$ai_skills_changelog" >"${ai_skills_changelog}.tmp"
		printf '%s\n\n' "$new_entry" >>"${ai_skills_changelog}.tmp"
		tail -n +"$first_version_line" "$ai_skills_changelog" >>"${ai_skills_changelog}.tmp"
		mv "${ai_skills_changelog}.tmp" "$ai_skills_changelog"
		echo "  Changelog entry added for v${version}"
	else
		echo "  WARNING: Could not find version entry in ai-skills CHANGELOG, skipping"
	fi
else
	if [[ -n "$release_notes" ]]; then
		echo "  WARNING: release notes are non-empty but no skill-related entries matched the filter."
		echo "           The ai-skills CHANGELOG sync produced nothing — the plugin CHANGELOG bullet format"
		echo "           may have changed and broken the grep filter (skill_notes pattern above). Skill"
		echo "           changes will NOT reach the ai-skills CHANGELOG until the pattern is fixed."
	else
		echo "  No skill changes to add to changelog"
	fi
fi

cd "$AI_SKILLS_DIR"
if [[ -n "$(git status --porcelain)" ]]; then
	git add -A
	git commit -m "sync: v${version} from whetstone plugin"
else
	echo "  ai-skills has no mirror changes"
fi
ai_skills_sha=$(git rev-parse HEAD)
push_release_sha "$AI_SKILLS_DIR" "ai-skills" "$ai_skills_sha"
echo "  ai-skills at $ai_skills_sha on origin/$RELEASE_BRANCH"

# Create GitHub release on ai-skills
if gh release view "v${version}" &>/dev/null; then
	echo "  ai-skills release v${version} already exists, skipping"
else
	gh release create "v${version}" \
		--title "v${version}" \
		--notes "Synced from whetstone plugin v${version}" \
		--target "$ai_skills_sha"
	echo "  ai-skills release v${version} created"
fi
cd "$ROOT_DIR"

# --- 5. Publish to ClawHub ---
# Non-fatal: a publish failure must not abort the remaining local steps
# (sync-to-tools, update-plugin, tag fetch-back). Status is surfaced loudly in
# the final summary with an exact resume command.
echo "[5/9] Publish skills to ClawHub..."
clawhub_status="published"
if "${CLAWHUB_CLI[@]}" whoami >/dev/null 2>&1; then
	if bash "$SCRIPT_DIR/publish-clawhub.sh"; then
		echo "  Published to ClawHub"
	else
		clawhub_status="failed"
		echo "  WARNING: ClawHub publish failed — continuing with remaining local steps."
	fi
else
	clawhub_status="skipped-unauth"
	echo "  WARNING: Not authenticated to ClawHub, skipping. Run: npx clawhub@${CLAWHUB_VERSION} login"
fi

# --- 6. Sync to shared skill directories (Agents, Kilocode) ---
echo "[6/9] Sync skills to other tools..."
bash "$SCRIPT_DIR/sync-to-tools.sh"

# --- 7. Update local plugin ---
echo "[7/9] Update local plugin..."
bash "$SCRIPT_DIR/update-plugin.sh"

# --- 8. Sync tags ---
# `gh release create` created the tag on the remote only; fetch it so local
# `git tag` and `git log v<ver>..HEAD` match origin.
echo "[8/9] Sync tags from origin..."
git fetch --tags --quiet
echo "  Tags synced"

# --- 9. Summary ---
echo ""
echo "[9/9] Done. v${version} released."
echo "  Restart Claude Code to pick up the new version."
echo "  Start a new Codex thread to pick up the refreshed native plugin."

if [[ "$clawhub_status" != "published" ]]; then
	echo ""
	echo "============================================================"
	echo "  ACTION REQUIRED: ClawHub publish did not complete"
	if [[ "$clawhub_status" == "skipped-unauth" ]]; then
		echo "    Reason: not authenticated to ClawHub (publish skipped)."
		echo "    Resume: npx clawhub@${CLAWHUB_VERSION} login && bash scripts/publish-clawhub.sh"
	else
		echo "    Reason: publish-clawhub.sh exited non-zero."
		echo "    Resume: bash scripts/publish-clawhub.sh"
	fi
	echo "    Commit, push, mirror, and local sync all completed;"
	echo "    only the ClawHub registry is missing v${version}."
	echo "============================================================"
fi
