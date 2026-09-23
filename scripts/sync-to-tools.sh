#!/usr/bin/env bash
set -Eeuo pipefail

# Symlink plugin skills to shared non-Claude tool directories.
# Claude Code and Codex get skills through their native plugins.
#
# Destination names match plugin source names (ia-<name>).
#
# Usage: bash scripts/sync-to-tools.sh [--dry-run]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILLS_DIR="$REPO_ROOT/plugins/whetstone/skills"

TOOL_DIRS=(
	"$HOME/.agents/skills"
	"$HOME/.kilocode/skills"
)
CODEX_HOME_DIR="${CODEX_HOME:-$HOME/.codex}"
CODEX_SKILLS_DIR="$CODEX_HOME_DIR/skills"

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

added=0
unchanged=0
removed=0
legacy_codex_removed=0

# Collect plugin skill names
plugin_skills=()
for skill_dir in "$SKILLS_DIR"/*/; do
	[[ -d "$skill_dir" ]] || continue
	[[ -f "$skill_dir/SKILL.md" ]] || continue
	plugin_skills+=("$(basename "$skill_dir")")
done

# Native Codex plugin installation supersedes the old direct skill links.
# Remove only symlinks owned by this checkout after confirming that replacement.
codex_plugin_installed=false
if command -v codex >/dev/null 2>&1 && codex plugin list 2>/dev/null | grep -Eq '^whetstone@whetstone[[:space:]]+installed, enabled([[:space:]]|$)'; then
	codex_plugin_installed=true
fi

if [[ "$codex_plugin_installed" == true && -d "$CODEX_SKILLS_DIR" ]]; then
	for link in "$CODEX_SKILLS_DIR"/*; do
		[[ -L "$link" ]] || continue
		link_target=$(readlink -f "$link" 2>/dev/null || true)
		[[ "$link_target" == "$SKILLS_DIR/"* ]] || continue

		printf "  - codex: %s (native plugin supersedes link)\n" "$(basename "$link")"
		[[ "$DRY_RUN" == false ]] && rm -- "$link"
		removed=$((removed + 1))
		legacy_codex_removed=$((legacy_codex_removed + 1))
	done
fi

for tool_dir in "${TOOL_DIRS[@]}"; do
	tool_name=$(basename "$(dirname "$tool_dir")")
	[[ "$DRY_RUN" == false ]] && mkdir -p "$tool_dir"

	# Add/update symlinks
	for skill in "${plugin_skills[@]}"; do
		target="$SKILLS_DIR/$skill"
		link="$tool_dir/$skill"

		if [[ -L "$link" ]]; then
			current=$(readlink -f "$link" 2>/dev/null || true)
			if [[ "$current" == "$(readlink -f "$target")" ]]; then
				unchanged=$((unchanged + 1))
				continue
			fi
			[[ "$DRY_RUN" == false ]] && rm "$link"
		fi

		printf "  + %s: %s\n" "$tool_name" "$skill"
		[[ "$DRY_RUN" == false ]] && ln -sf "$target" "$link"
		added=$((added + 1))
	done

	# Remove stale symlinks pointing into our skills dir
	for link in "$tool_dir"/*; do
		[[ -L "$link" ]] || continue
		link_target=$(readlink "$link" 2>/dev/null || true)
		[[ "$link_target" == "$SKILLS_DIR"* ]] || continue

		name=$(basename "$link")
		found=0
		for skill in "${plugin_skills[@]}"; do
			[[ "$skill" == "$name" ]] && found=1 && break
		done

		if [[ "$found" -eq 0 ]]; then
			printf "  - %s: %s (removed)\n" "$tool_name" "$name"
			[[ "$DRY_RUN" == false ]] && rm "$link"
			removed=$((removed + 1))
		fi
	done
done

printf "\nSynced %d skills to %d tools: +%d -%d =%d\n" \
	"${#plugin_skills[@]}" "${#TOOL_DIRS[@]}" "$added" "$removed" "$unchanged"
printf "Removed %d legacy Codex skill link(s).\n" "$legacy_codex_removed"

if [[ "$codex_plugin_installed" == true ]]; then
	if [[ "$DRY_RUN" == true ]]; then
		python3 "$SCRIPT_DIR/configure-codex-skill-sources.py" --codex-home "$CODEX_HOME_DIR" --dry-run >/dev/null
		printf "Would refresh managed Codex skill-source exclusions.\n"
	else
		python3 "$SCRIPT_DIR/configure-codex-skill-sources.py" --codex-home "$CODEX_HOME_DIR"
	fi
else
	if [[ "$DRY_RUN" == true ]]; then
		python3 "$SCRIPT_DIR/configure-codex-skill-sources.py" --codex-home "$CODEX_HOME_DIR" --remove --dry-run >/dev/null
		printf "Would remove managed Codex skill-source exclusions.\n"
	else
		python3 "$SCRIPT_DIR/configure-codex-skill-sources.py" --codex-home "$CODEX_HOME_DIR" --remove
	fi
fi

if [[ "$DRY_RUN" == true ]]; then
	printf "\n  (dry run — no changes made)\n"
fi
