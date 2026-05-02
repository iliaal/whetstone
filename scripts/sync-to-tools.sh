#!/usr/bin/env bash
set -Eeuo pipefail

# Symlink plugin skills to non-Claude tool directories.
# Claude Code gets skills via the plugin; other tools need symlinks.
#
# Shared-dir destination names match plugin source names (ia-<name>) — keeps
# invocations short. Slug rebranding to whetstone-<name> would double the
# typed length for no functional gain in shared dirs.
#
# Usage: bash scripts/sync-to-tools.sh [--dry-run]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILLS_DIR="$REPO_ROOT/plugins/whetstone/skills"

TOOL_DIRS=(
  "$HOME/.agents/skills"
  "$HOME/.codex/skills"
  "$HOME/.kilocode/skills"
)

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

added=0
unchanged=0
removed=0

# Collect plugin skill names
plugin_skills=()
for skill_dir in "$SKILLS_DIR"/*/; do
  [[ -d "$skill_dir" ]] || continue
  [[ -f "$skill_dir/SKILL.md" ]] || continue
  plugin_skills+=("$(basename "$skill_dir")")
done

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

if [[ "$DRY_RUN" == true ]]; then
  printf "\n  (dry run — no changes made)\n"
fi
