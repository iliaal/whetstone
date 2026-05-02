#!/usr/bin/env bash
set -euo pipefail

# PreToolUse hook for Task tool — injects relevant skill file paths into subagent prompts.
# Fires before every Task tool call. Matches the subagent prompt against skill trigger
# patterns and prepends "Read these SKILL.md files" instructions via updatedInput.

INPUT=$(cat)

# Extract prompt and subagent type
PROMPT=$(printf '%s' "$INPUT" | jq -r '.tool_input.prompt // empty')
AGENT_TYPE=$(printf '%s' "$INPUT" | jq -r '.tool_input.subagent_type // empty')

# Nothing to match against
if [[ -z "$PROMPT" ]]; then
  exit 0
fi

# Skip agent types that can't read files
case "$AGENT_TYPE" in
  Bash|statusline-setup) exit 0 ;;
esac

# Resolve paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PATTERNS_FILE="$SCRIPT_DIR/skill-patterns.sh"

if [[ ! -f "$PATTERNS_FILE" ]]; then
  exit 0
fi

# shellcheck source=skill-patterns.sh
source "$PATTERNS_FILE"

# Guard: older pattern files may not declare SKILL_PROJECT_TYPES
if ! declare -p SKILL_PROJECT_TYPES &>/dev/null; then
  declare -A SKILL_PROJECT_TYPES
fi

# Guard: older pattern files may not declare SKILL_MAINT_SUPPRESS
if ! declare -p SKILL_MAINT_SUPPRESS &>/dev/null; then
  declare -A SKILL_MAINT_SUPPRESS
fi

# Detect plugin-maintenance context. When the prompt mentions plugin internals,
# skill files, or maintenance commands, skills whose names appear as references
# shouldn't fire as if the user is invoking them.
IS_MAINT_CONTEXT=false
if printf '%s' "$PROMPT" | grep -qE 'plugins/whetstone/(skills|agents|commands)/|distiller\.py|skill-patterns\.sh|/sync-from-repos\b|/audit-plugin\b|/analyze-misfires\b|/diagnose-negatives\b|/evolve-skill\b|/eval-skills\b' 2>/dev/null; then
  IS_MAINT_CONTEXT=true
fi

# Detect project types from marker files in working directory.
# Used as a negative filter: domain skills that declare a project type
# are suppressed when the project stack doesn't match.
PROJECT_TYPES=()
[[ -f "composer.json" || -f "artisan" ]] && PROJECT_TYPES+=("php")
[[ -f "package.json" ]] && PROJECT_TYPES+=("js")
[[ -f "pyproject.toml" || -f "setup.py" || -f "requirements.txt" ]] && PROJECT_TYPES+=("python")
[[ -f "Cargo.toml" ]] && PROJECT_TYPES+=("rust")
[[ -f "go.mod" ]] && PROJECT_TYPES+=("go")
compgen -G "*.tf" > /dev/null 2>&1 && PROJECT_TYPES+=("terraform")

# Lowercase prompt for case-insensitive matching
PROMPT_LOWER=$(printf '%s' "$PROMPT" | tr '[:upper:]' '[:lower:]')

# Collect matching skills into tier buckets
TIER1=()
TIER2=()
TIER3=()

for skill_name in "${!SKILL_PATTERNS[@]}"; do
  pattern="${SKILL_PATTERNS[$skill_name]}"
  if printf '%s' "$PROMPT_LOWER" | grep -qE "$pattern" 2>/dev/null; then
    skill_path="$PLUGIN_ROOT/skills/$skill_name/SKILL.md"
    [[ -f "$skill_path" ]] || continue

    # Suppress skills whose name tends to appear as a reference in plugin-maintenance
    # prompts (skill name in file path, command discussion, distiller output, etc.).
    if $IS_MAINT_CONTEXT && [[ -n "${SKILL_MAINT_SUPPRESS[$skill_name]+x}" ]]; then
      continue
    fi

    # Suppress skills whose project-type constraint doesn't match.
    # Only filters when both: (a) skill declares a type, (b) we detected types.
    if [[ -n "${SKILL_PROJECT_TYPES[$skill_name]+x}" ]] && [[ ${#PROJECT_TYPES[@]} -gt 0 ]]; then
      _required="${SKILL_PROJECT_TYPES[$skill_name]}"
      _match=false
      for _pt in "${PROJECT_TYPES[@]}"; do
        [[ "$_pt" == "$_required" ]] && { _match=true; break; }
      done
      $_match || continue
    fi

    tier="${SKILL_TIERS[$skill_name]}"
    case "$tier" in
      1) TIER1+=("$skill_name") ;;
      2) TIER2+=("$skill_name") ;;
      3) TIER3+=("$skill_name") ;;
    esac
  fi
done

# Combine in priority order
ALL_MATCHES=()
[[ ${#TIER1[@]} -gt 0 ]] && ALL_MATCHES+=("${TIER1[@]}")
[[ ${#TIER2[@]} -gt 0 ]] && ALL_MATCHES+=("${TIER2[@]}")
[[ ${#TIER3[@]} -gt 0 ]] && ALL_MATCHES+=("${TIER3[@]}")

if [[ ${#ALL_MATCHES[@]} -eq 0 ]]; then
  exit 0
fi

# Cap at 5 skills to avoid context bloat
MAX_SKILLS=5
if [[ ${#ALL_MATCHES[@]} -gt $MAX_SKILLS ]]; then
  ALL_MATCHES=("${ALL_MATCHES[@]:0:$MAX_SKILLS}")
fi

# Log injected skills when running in test mode (zero overhead otherwise)
if [[ -n "${TEST_INJECTION_LOG:-}" ]]; then
  for skill_name in "${ALL_MATCHES[@]}"; do
    printf '%s\n' "$skill_name" >> "$TEST_INJECTION_LOG"
  done
fi

# Build injection text
INJECTION="BEFORE STARTING: Read and follow these skill files for methodology and patterns relevant to this task:"
for skill_name in "${ALL_MATCHES[@]}"; do
  INJECTION="$INJECTION
- ${PLUGIN_ROOT}/skills/${skill_name}/SKILL.md"
done
INJECTION="$INJECTION
If you cannot read the files, proceed with your best judgment."

# Prepend injection to original prompt
MODIFIED_PROMPT=$(printf '%s\n\n%s' "$INJECTION" "$PROMPT")

# Output updatedInput — must include ALL original tool_input fields since
# updatedInput is a full replacement, not a merge. Only the prompt changes.
TOOL_INPUT=$(printf '%s' "$INPUT" | jq '.tool_input')
printf '%s' "$TOOL_INPUT" | jq --arg prompt "$MODIFIED_PROMPT" '{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "updatedInput": (. + {"prompt": $prompt})
  }
}'
