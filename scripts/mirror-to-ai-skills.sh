#!/usr/bin/env bash
set -Eeuo pipefail

# Mirror plugin skills to ai-skills public repo (read-only distribution)
# Usage: bash scripts/mirror-to-ai-skills.sh [--dry-run]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE_DIR="$REPO_ROOT/plugins/whetstone/skills"
TARGET_REPO="$HOME/ai/ai-skills"
TARGET_DIR="$TARGET_REPO/skills"
SOURCE_LICENSE="$REPO_ROOT/LICENSE"
TARGET_LICENSE="$TARGET_REPO/LICENSE"
TARGET_BRANCH="master"

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

added=0
updated=0
removed=0
unchanged=0

printf "Source: %s\n" "$SOURCE_DIR"
printf "Target: %s\n\n" "$TARGET_DIR"

# A missing checkout is not an intentionally empty skill set. Abort before
# staging, target updates, retirement, or license synchronization.
if [[ ! -d "$SOURCE_DIR" ]]; then
    printf "ERROR: Source directory does not exist: %s\n" "$SOURCE_DIR" >&2
    exit 1
fi

is_mirrorable_skill() {
    [[ -d "$1" && -f "$1/SKILL.md" ]]
}

if [[ ! -d "$TARGET_DIR" ]]; then
    printf "ERROR: Target directory does not exist: %s\n" "$TARGET_DIR" >&2
    printf "Clone ai-skills repo first: git clone <url> %s\n" "$(dirname "$TARGET_DIR")" >&2
    exit 1
fi

# The release commits and pushes whatever this writes, so mirroring onto any
# branch other than the one release.sh pushes would publish nothing or the wrong tree.
target_branch=$(git -C "$TARGET_REPO" symbolic-ref --quiet --short HEAD 2>/dev/null || true)
if [[ "$target_branch" != "$TARGET_BRANCH" ]]; then
    printf "ERROR: %s is on '%s', not '%s'. Check out %s before mirroring.\n" \
        "$TARGET_REPO" "${target_branch:-detached HEAD or not a git repo}" "$TARGET_BRANCH" "$TARGET_BRANCH" >&2
    exit 1
fi

# Compare and publish the same normalized tree, so repeated runs (including
# --dry-run) leave unchanged destinations alone. Staging is removed on failure.
stage_root=$(mktemp -d)
trap 'rm -rf "$stage_root"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Mirror: source → target. Plugin dirs are "ia-<name>"; strip the ia- prefix
# before writing into ai-skills so existing installs keep working with the
# original skill names (debugging/, writing/, etc.).
for skill_dir in "$SOURCE_DIR"/*/; do
    is_mirrorable_skill "$skill_dir" || continue
    plugin_name="$(basename "$skill_dir")"

    # Strip the in-plugin ia- prefix for the mirror destination
    skill_name="${plugin_name#ia-}"
    target_dir="$TARGET_DIR/$skill_name"

    staged_dir="$stage_root/skill"
    rm -rf "$staged_dir"
    cp -r "$skill_dir" "$staged_dir"
    # Bytecode from local script runs must not enter the distribution.
    find "$staged_dir" -type d -name __pycache__ -prune -exec rm -rf {} +
    sed -i -E "0,/^name: *ia-$skill_name$/s//name: $skill_name/" "$staged_dir/SKILL.md"

    if [[ -d "$target_dir" ]]; then
        if diff -rq "$staged_dir" "$target_dir" >/dev/null 2>&1; then
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
        cp -r "$staged_dir" "$target_dir"
    fi
done

# Cleanup uses the same eligibility as copying, including legacy unprefixed skills.
for skill_dir in "$TARGET_DIR"/*/; do
    [[ -d "$skill_dir" ]] || continue
    skill_name="$(basename "$skill_dir")"

    # Source uses the ia- prefix; reverse the strip to check existence
    if ! is_mirrorable_skill "$SOURCE_DIR/ia-$skill_name" \
        && ! is_mirrorable_skill "$SOURCE_DIR/$skill_name"; then
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
