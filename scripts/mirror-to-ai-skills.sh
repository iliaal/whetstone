#!/usr/bin/env bash
set -Eeuo pipefail

# Mirror plugin skills to ai-skills public repo (read-only distribution)
# Usage: bash scripts/mirror-to-ai-skills.sh [--dry-run]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE_DIR="$REPO_ROOT/plugins/whetstone/skills"
TARGET_DIR="$HOME/ai/ai-skills/skills"
SOURCE_LICENSE="$REPO_ROOT/LICENSE"
TARGET_LICENSE="$HOME/ai/ai-skills/LICENSE"

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

added=0
updated=0
removed=0
unchanged=0

printf "Source: %s\n" "$SOURCE_DIR"
printf "Target: %s\n\n" "$TARGET_DIR"

if [[ ! -d "$TARGET_DIR" ]]; then
    printf "ERROR: Target directory does not exist: %s\n" "$TARGET_DIR" >&2
    printf "Clone ai-skills repo first: git clone <url> %s\n" "$(dirname "$TARGET_DIR")" >&2
    exit 1
fi

# Mirror: source → target. Plugin dirs are "ia-<name>"; strip the ia- prefix
# before writing into ai-skills so existing installs keep working with the
# original skill names (debugging/, writing/, etc.).
for skill_dir in "$SOURCE_DIR"/*/; do
    [[ -d "$skill_dir" ]] || continue
    plugin_name="$(basename "$skill_dir")"
    [[ -f "$skill_dir/SKILL.md" ]] || continue

    # Strip the in-plugin ia- prefix for the mirror destination
    skill_name="${plugin_name#ia-}"
    target_dir="$TARGET_DIR/$skill_name"

    if [[ -d "$target_dir" ]]; then
        if diff -rq "$skill_dir" "$target_dir" >/dev/null 2>&1; then
            unchanged=$((unchanged + 1))
            continue
        fi
        action="updated"
        updated=$((updated + 1))
    else
        action="added"
        added=$((added + 1))
    fi

    printf "  %-10s %s\n" "$action" "$skill_name"

    if [[ "$DRY_RUN" == false ]]; then
        rm -rf "$target_dir"
        cp -r "$skill_dir" "$target_dir"
        # Rewrite the mirrored SKILL.md frontmatter name: back to the un-prefixed form
        if [[ -f "$target_dir/SKILL.md" ]]; then
            sed -i -E "0,/^name: *ia-$skill_name$/s//name: $skill_name/" "$target_dir/SKILL.md"
        fi
    fi
done

# Cleanup: remove from target if the corresponding "ia-<name>" dir is absent in source
for skill_dir in "$TARGET_DIR"/*/; do
    [[ -d "$skill_dir" ]] || continue
    skill_name="$(basename "$skill_dir")"

    # Source uses the ia- prefix; reverse the strip to check existence
    if [[ ! -d "$SOURCE_DIR/ia-$skill_name" && ! -d "$SOURCE_DIR/$skill_name" ]]; then
        printf "  %-10s %s\n" "removed" "$skill_name"
        removed=$((removed + 1))
        if [[ "$DRY_RUN" == false ]]; then
            rm -rf "$skill_dir"
        fi
    fi
done

# Mirror LICENSE from upstream
if [[ -f "$SOURCE_LICENSE" ]]; then
    if [[ ! -f "$TARGET_LICENSE" ]] || ! diff -q "$SOURCE_LICENSE" "$TARGET_LICENSE" >/dev/null 2>&1; then
        printf "  %-10s %s\n" "license" "LICENSE"
        [[ "$DRY_RUN" == false ]] && cp "$SOURCE_LICENSE" "$TARGET_LICENSE"
    fi
fi

printf "\n--- Mirror Summary ---\n"
printf "  Added:     %d\n" "$added"
printf "  Updated:   %d\n" "$updated"
printf "  Removed:   %d\n" "$removed"
printf "  Unchanged: %d\n" "$unchanged"
