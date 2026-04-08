#!/usr/bin/env bash
# Release pipeline: commit, push, mirror to ai-skills, update local plugin
# Usage: bash scripts/release.sh ["commit message"]
#   If no message provided, auto-generates from version + CHANGELOG headline
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
AI_SKILLS_DIR="$HOME/ai/ai-skills"

# --- Preflight ---
cd "$ROOT_DIR"

version=$(python3 -c "import json; print(json.load(open('plugins/compound-engineering/.claude-plugin/plugin.json'))['version'])")
marketplace_version=$(python3 -c "import json; print(json.load(open('.claude-plugin/marketplace.json'))['plugins'][0]['version'])")

if [[ "$version" != "$marketplace_version" ]]; then
  echo "ERROR: Version mismatch — plugin.json ($version) != marketplace.json ($marketplace_version)"
  exit 1
fi

# Check JSON validity
jq . .claude-plugin/marketplace.json > /dev/null || { echo "ERROR: marketplace.json is invalid JSON"; exit 1; }
jq . plugins/compound-engineering/.claude-plugin/plugin.json > /dev/null || { echo "ERROR: plugin.json is invalid JSON"; exit 1; }

# --- Pre-commit gates ---
echo "[Pre-commit] Running trigger regression tests..."
python3 distillery/scripts/distiller.py test-triggers > /dev/null || {
  echo "ERROR: Trigger regression tests failed. Fix patterns or fixtures before release."
  exit 1
}
echo "  Trigger tests passed"

echo "[Pre-commit] Running semantic injection tests..."
if python3 distillery/scripts/distiller.py test-semantic --max-tests 5 > /dev/null 2>&1; then
  echo "  Semantic tests passed"
else
  echo "  WARNING: Semantic tests had failures. Review output before proceeding."
fi

echo "[Pre-commit] Generating skill change manifest..."
python3 "$SCRIPT_DIR/generate-manifest.py"
echo "  Manifest updated"

# Check for staged/unstaged changes
if [[ -z "$(git status --porcelain)" ]]; then
  echo "ERROR: Nothing to commit"
  exit 1
fi

# Auto-generate commit message from CHANGELOG if not provided
if [[ -n "${1:-}" ]]; then
  commit_msg="$1"
else
  # Extract first content line after the version header in CHANGELOG
  changelog_headline=$(sed -n "/^## \[${version}\]/,/^## \[/{/^## \[${version}\]/d;/^## \[/d;/^$/d;/^###/{ s/^### //; p; q; }}" CHANGELOG.md 2>/dev/null)
  if [[ -n "$changelog_headline" ]]; then
    # Use changelog section name as summary
    commit_msg="bump: v${version} — $(echo "$changelog_headline" | tr '[:upper:]' '[:lower:]')"
  else
    commit_msg="bump: v${version}"
  fi
  echo "Commit message: $commit_msg"
fi

echo "=== Release v${version} ==="
echo ""

# --- 1. Commit & Push ---
echo "[1/6] Commit & push..."
git add -A -- \
  .claude-plugin/marketplace.json \
  CHANGELOG.md \
  distillery/.skill-versions.json \
  distillery/scripts/ \
  distillery/tests/ \
  scripts/ \
  plugins/compound-engineering/
# Also stage project-level skill changes if any
git add -A -- .claude/skills/ 2>/dev/null || true
git commit -m "$commit_msg"
git push origin main
echo "  Pushed to origin/main"

# --- 2. Sync GitHub repo description ---
echo "[2/7] Sync repo description..."
repo_desc=$(jq -r '.description' plugins/compound-engineering/.claude-plugin/plugin.json)
gh repo edit --description "$repo_desc" 2>/dev/null && echo "  Updated repo description" || echo "  Failed to update repo description (non-fatal)"

# --- 3. Create GitHub release on plugin repo ---
echo "[3/7] Create GitHub release..."
# Extract changelog entry for this version
release_notes=$(sed -n "/^## \[${version}\]/,/^## \[/{/^## \[${version}\]/d;/^## \[/d;p;}" CHANGELOG.md)
if gh release view "v${version}" &>/dev/null; then
  echo "  Release v${version} already exists, skipping"
else
  gh release create "v${version}" \
    --title "v${version}" \
    --notes "$release_notes" \
    --target main
  echo "  Created release v${version}"
fi

# --- 4. Mirror to ai-skills ---
echo "[4/7] Mirror to ai-skills..."
bash "$SCRIPT_DIR/mirror-to-ai-skills.sh"

# Sync changelog: extract skill-related entries from plugin changelog
echo "  Syncing changelog..."
# Build allowlist from actual skill directories (longest names first to avoid prefix conflicts)
skill_names=$(ls -1 "$ROOT_DIR/plugins/compound-engineering/skills" | awk '{print length, $0}' | sort -rn | awk '{print $2}' | tr '\n' '|' | sed 's/|$//')
# Keep ### headers and lines referencing known skills
skill_notes=$(printf '%s\n' "$release_notes" | grep -E "^### |^- \*\*(${skill_names})(\*\*|/)" || true)
# Strip orphan ### headers (headers with no entries after them)
skill_notes=$(printf '%s\n' "$skill_notes" | awk '/^### /{header=$0; next} /^- /{if(header){print header; header=""} print}')
if [[ -n "$skill_notes" ]]; then
  ai_skills_changelog="$AI_SKILLS_DIR/CHANGELOG.md"
  # Build new entry
  new_entry="## [${version}] - $(date +%Y-%m-%d)

${skill_notes}"
  # Insert after the header block (after the line matching "## [")
  # Find the line number of the first existing version entry
  first_version_line=$(grep -n '^## \[' "$ai_skills_changelog" | head -1 | cut -d: -f1)
  if [[ -n "$first_version_line" ]]; then
    head -n $((first_version_line - 1)) "$ai_skills_changelog" > "${ai_skills_changelog}.tmp"
    printf '%s\n\n' "$new_entry" >> "${ai_skills_changelog}.tmp"
    tail -n +"$first_version_line" "$ai_skills_changelog" >> "${ai_skills_changelog}.tmp"
    mv "${ai_skills_changelog}.tmp" "$ai_skills_changelog"
    echo "  Changelog entry added for v${version}"
  else
    echo "  WARNING: Could not find version entry in ai-skills CHANGELOG, skipping"
  fi
else
  echo "  No skill changes to add to changelog"
fi

cd "$AI_SKILLS_DIR"
if [[ -n "$(git status --porcelain)" ]]; then
  git add -A
  git commit -m "sync: v${version} from compound-engineering plugin"
  git push origin master
  echo "  ai-skills pushed"
else
  echo "  ai-skills already up to date"
fi

# Create GitHub release on ai-skills
if gh release view "v${version}" &>/dev/null; then
  echo "  ai-skills release v${version} already exists, skipping"
else
  gh release create "v${version}" \
    --title "v${version}" \
    --notes "Synced from compound-engineering plugin v${version}" \
    --target master
  echo "  ai-skills release v${version} created"
fi
cd "$ROOT_DIR"

# --- 5. Publish to ClawHub ---
echo "[5/8] Publish skills to ClawHub..."
if npx clawhub@latest whoami >/dev/null 2>&1; then
  bash "$SCRIPT_DIR/publish-clawhub.sh"
else
  echo "  WARNING: Not authenticated to ClawHub, skipping. Run: npx clawhub@latest login"
fi

# --- 6. Sync to other tools (Codex, Kilocode, etc.) ---
echo "[6/8] Sync skills to other tools..."
bash "$SCRIPT_DIR/sync-to-tools.sh"

# --- 7. Update local plugin ---
echo "[7/8] Update local plugin..."
bash "$SCRIPT_DIR/update-plugin.sh"

# --- 8. Summary ---
echo ""
echo "[8/8] Done. v${version} released."
echo "  Restart Claude Code to pick up the new version."
