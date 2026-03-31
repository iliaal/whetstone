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
