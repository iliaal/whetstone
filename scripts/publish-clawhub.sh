#!/usr/bin/env bash
set -Eeuo pipefail

# Publish plugin skills to clawhub.ai registry
# Usage: bash scripts/publish-clawhub.sh [--dry-run] [--skill <name>]
#
# Prerequisites:
#   npx clawhub@latest login --token <token>
#
# Publishes each skill with slug "compound-eng-<skill-name>".
# Handles rate limits (5 new skills/hour) by waiting and retrying.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILLS_DIR="$REPO_ROOT/plugins/compound-engineering/skills"
PLUGIN_JSON="$REPO_ROOT/plugins/compound-engineering/.claude-plugin/plugin.json"

SLUG_PREFIX="compound-eng"
DRY_RUN=false
SINGLE_SKILL=""
MAX_RETRIES=6
RATE_LIMIT_WAIT=720

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=true; shift ;;
        --skill)   SINGLE_SKILL="$2"; shift 2 ;;
        -h|--help)
            printf "Usage: %s [--dry-run] [--skill <name>]\n" "$(basename "$0")"
            printf "\nOptions:\n"
            printf "  --dry-run       Show what would be published without publishing\n"
            printf "  --skill <name>  Publish a single skill instead of all\n"
            exit 0
            ;;
        *) printf "Unknown option: %s\n" "$1" >&2; exit 1 ;;
    esac
done

VERSION=$(grep -o '"version": *"[^"]*"' "$PLUGIN_JSON" | head -1 | cut -d'"' -f4)
printf "Plugin version: %s\n" "$VERSION"
printf "Skills dir:     %s\n" "$SKILLS_DIR"
printf "Slug prefix:    %s-\n\n" "$SLUG_PREFIX"

if [[ "$DRY_RUN" == false ]]; then
    if ! npx clawhub@latest whoami >/dev/null 2>&1; then
        printf "ERROR: Not authenticated. Run: npx clawhub@latest login --token <token>\n" >&2
        exit 1
    fi
fi

published=0
skipped=0
failed=0
errors=()

publish_skill() {
    local skill_dir="$1"
    local skill_name
    skill_name="$(basename "$skill_dir")"

    if [[ ! -f "$skill_dir/SKILL.md" ]]; then
        printf "  %-12s %s (no SKILL.md)\n" "skipped" "$skill_name"
        skipped=$((skipped + 1))
        return
    fi

    local slug="${SLUG_PREFIX}-${skill_name}"
    local display_name
    display_name=$(grep -m1 '^name:' "$skill_dir/SKILL.md" | sed 's/^name: *//' | tr -d "'\"")

    if [[ "$DRY_RUN" == true ]]; then
        printf "  %-12s %s → %s (v%s)\n" "would publish" "$skill_name" "$slug" "$VERSION"
        published=$((published + 1))
        return
    fi

    local inspect_output
    if inspect_output=$(npx clawhub@latest inspect "$slug" 2>&1); then
        if [[ "$inspect_output" == *"$VERSION"* ]]; then
            printf "  %-12s %s → %s (v%s)\n" "exists" "$skill_name" "$slug" "$VERSION"
            skipped=$((skipped + 1))
            return
        fi
    fi

    local retries=0
    while true; do
        printf "  %-12s %s → %s ... " "publishing" "$skill_name" "$slug"

        local output
        if output=$(npx clawhub@latest publish "$skill_dir" \
            --slug "$slug" \
            --name "${display_name:-$skill_name}" \
            --version "$VERSION" \
            --changelog "v${VERSION}" \
            --tags "latest" 2>&1); then
            printf "ok\n"
            published=$((published + 1))
            return
        elif [[ "$output" == *"Version already exists"* ]]; then
            printf "exists (v%s)\n" "$VERSION"
            skipped=$((skipped + 1))
            return
        elif [[ "$output" == *"Rate limit"* || "$output" == *"rate limit"* ]] && (( retries < MAX_RETRIES )); then
            retries=$((retries + 1))
            printf "rate limited (attempt %d/%d, waiting %ds)\n" "$retries" "$MAX_RETRIES" "$RATE_LIMIT_WAIT"
            sleep "$RATE_LIMIT_WAIT"
        else
            printf "FAILED\n"
            errors+=("$skill_name: $output")
            failed=$((failed + 1))
            return
        fi
    done
}

if [[ -n "$SINGLE_SKILL" ]]; then
    skill_path="$SKILLS_DIR/$SINGLE_SKILL"
    if [[ ! -d "$skill_path" ]]; then
        printf "ERROR: Skill not found: %s\n" "$skill_path" >&2
        exit 1
    fi
    publish_skill "$skill_path"
else
    for skill_dir in "$SKILLS_DIR"/*/; do
        [[ -d "$skill_dir" ]] || continue
        publish_skill "$skill_dir"
    done
fi

printf "\n--- ClawHub Publish Summary ---\n"
printf "  Published: %d\n" "$published"
printf "  Skipped:   %d\n" "$skipped"
printf "  Failed:    %d\n" "$failed"

if [[ ${#errors[@]} -gt 0 ]]; then
    printf "\nErrors:\n"
    for err in "${errors[@]}"; do
        printf "  %s\n" "$err"
    done
    exit 1
fi
