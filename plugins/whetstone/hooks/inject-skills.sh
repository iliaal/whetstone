#!/usr/bin/env bash
set -euo pipefail

# PreToolUse hook for Task tool — injects relevant skill file paths into subagent prompts.
# Fires before every Task tool call. Matches the subagent prompt against skill trigger
# patterns and prepends "Read these SKILL.md files" instructions via updatedInput.

# Skill injection is an enhancement, never a precondition for running a subagent.
# A missing dependency or a malformed payload must degrade to "no injection", not to
# a visible hook error on every Task call, so bail out silently rather than failing.
command -v jq >/dev/null 2>&1 || exit 0
trap 'exit 0' ERR

INPUT=$(cat)
printf '%s' "$INPUT" | jq -e '
  (.tool_input | type == "object") and
  (.tool_input.prompt | type == "string") and
  ((.tool_input.subagent_type // "") | type == "string")
' >/dev/null || exit 0

# Extract prompt and subagent type
PROMPT=$(printf '%s' "$INPUT" | jq -r '.tool_input.prompt // empty')
AGENT_TYPE=$(printf '%s' "$INPUT" | jq -r '.tool_input.subagent_type // empty')

# Nothing to match against
if [[ -z "$PROMPT" ]]; then
  exit 0
fi

# Skip agent types that can't read files
case "$AGENT_TYPE" in
  Bash | statusline-setup) exit 0 ;;
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

# Guard: older pattern files may not declare SKILL_MAINT_SUPPRESS
if ! declare -p SKILL_MAINT_SUPPRESS &>/dev/null; then
  declare -A SKILL_MAINT_SUPPRESS
fi

# Guard: older pattern files may not declare SKILL_NEGATIVE
if ! declare -p SKILL_NEGATIVE &>/dev/null; then
  declare -A SKILL_NEGATIVE
fi

# Detect plugin-maintenance context. When the prompt mentions plugin internals,
# skill files, or maintenance commands, skills whose names appear as references
# shouldn't fire as if the user is invoking them.
IS_MAINT_CONTEXT=false
if printf '%s' "$PROMPT" | grep -qiE 'plugins/whetstone/(skills|agents|commands)/|skill-patterns\.sh|/sync-from-repos\b|/audit-plugin\b|/(analyze-misfires|diagnose-negatives|evolve-skill|eval-skills)\b|^run .{0,80}distiller\.py +(analyze-misfires|diagnose-negatives)\b' 2>/dev/null; then
  IS_MAINT_CONTEXT=true
fi

# Lowercase prompt for case-insensitive matching
PROMPT_LOWER=$(printf '%s' "$PROMPT" | tr '[:upper:]' '[:lower:]')

# Collect matching skills into tier buckets
TIER1=()
TIER2=()
TIER3=()

readarray -t SKILL_NAMES < <(printf '%s\n' "${!SKILL_PATTERNS[@]}" | LC_ALL=C sort)
for skill_name in "${SKILL_NAMES[@]}"; do
  pattern="${SKILL_PATTERNS[$skill_name]}"
  if printf '%s' "$PROMPT_LOWER" | grep -qE "$pattern" 2>/dev/null; then
    skill_path="$PLUGIN_ROOT/skills/$skill_name/SKILL.md"
    [[ -f "$skill_path" ]] || continue

    # Suppress when the prompt carries an explicit marker for a NEIGHBOURING language
    # or stack. SKILL_PATTERNS cannot express "X unless Y" (ERE has no lookahead), so
    # a language-neutral alternative like `segfault` or `\.h\b` otherwise fires the C
    # skill on a C# or Objective-C prompt. Keep entries to unambiguous markers; this is
    # not a place to fix a positive pattern that is merely too loose.
    if [[ -n "${SKILL_NEGATIVE[$skill_name]+x}" ]]; then
      if printf '%s' "$PROMPT_LOWER" | grep -qE "${SKILL_NEGATIVE[$skill_name]}" 2>/dev/null; then
        continue
      fi
    fi

    # Suppress skills whose name tends to appear as a reference in plugin-maintenance
    # prompts (skill name in file path, command discussion, distiller output, etc.).
    if $IS_MAINT_CONTEXT && [[ -n "${SKILL_MAINT_SUPPRESS[$skill_name]+x}" ]]; then
      continue
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

# Cap at 5 skills to avoid context bloat
MAX_SKILLS=5
if [[ ${#ALL_MATCHES[@]} -gt $MAX_SKILLS ]]; then
  ALL_MATCHES=("${ALL_MATCHES[@]:0:$MAX_SKILLS}")
fi
REGEX_MATCH_COUNT=${#ALL_MATCHES[@]}

if [[ "${WHETSTONE_JEV:-}" == 1 && ${#ALL_MATCHES[@]} -lt $MAX_SKILLS ]] &&
  command -v python3 >/dev/null 2>&1 && command -v "${WHETSTONE_JEV_COMMAND:-jev}" >/dev/null 2>&1; then
  ELIGIBLE=()
  for skill_name in "${SKILL_NAMES[@]}"; do
    [[ -f "$PLUGIN_ROOT/skills/$skill_name/SKILL.md" ]] || continue
    [[ " ${ALL_MATCHES[*]-} " == *" $skill_name "* ]] && continue
    if [[ -n "${SKILL_NEGATIVE[$skill_name]+x}" ]] &&
      printf '%s' "$PROMPT_LOWER" | grep -qE "${SKILL_NEGATIVE[$skill_name]}" 2>/dev/null; then
      continue
    fi
    if $IS_MAINT_CONTEXT && [[ -n "${SKILL_MAINT_SUPPRESS[$skill_name]+x}" ]]; then
      continue
    fi
    ELIGIBLE+=("$skill_name")
  done
  JEV_CMD=(python3 "$SCRIPT_DIR/jev-skills.py" "$PLUGIN_ROOT/skills")
  if [[ ${#ALL_MATCHES[@]} -gt 0 ]]; then
    JEV_CMD+=(--selected "${ALL_MATCHES[@]}")
  fi
  JEV_CMD+=(-- ${ELIGIBLE[@]+"${ELIGIBLE[@]}"})
  if [[ ${#ELIGIBLE[@]} -gt 0 ]] &&
    JEV_MATCHES=$(printf '%s' "$INPUT" | "${JEV_CMD[@]}" 2>/dev/null); then
    while IFS= read -r skill_name; do
      [[ -n "$skill_name" ]] || continue
      ALL_MATCHES+=("$skill_name")
      [[ ${#ALL_MATCHES[@]} -lt $MAX_SKILLS ]] || break
    done <<<"$JEV_MATCHES"
  fi
fi

if [[ ${#ALL_MATCHES[@]} -eq 0 ]]; then
  exit 0
fi

# Log injected skills when running in test mode (zero overhead otherwise)
if [[ -n "${TEST_INJECTION_LOG:-}" ]]; then
  for skill_name in "${ALL_MATCHES[@]}"; do
    printf '%s\n' "$skill_name" >>"$TEST_INJECTION_LOG"
  done
fi

# Build injection text
INJECTION="BEFORE STARTING: Read and follow these skill files for methodology and patterns relevant to this task:"
if [[ $REGEX_MATCH_COUNT -eq 0 ]]; then
  INJECTION="BEFORE STARTING: Jev suggests these skill files; check applicability before following their instructions:"
fi
for index in "${!ALL_MATCHES[@]}"; do
  skill_name="${ALL_MATCHES[$index]}"
  if [[ $index -eq $REGEX_MATCH_COUNT && $index -gt 0 ]]; then
    INJECTION="$INJECTION
Additional skill suggestions (Jev; check applicability before following):"
  fi
  INJECTION="$INJECTION
- ${PLUGIN_ROOT}/skills/${skill_name}/SKILL.md"
done
INJECTION="$INJECTION
If you cannot read the files, proceed with your best judgment."

# Output updatedInput — must include ALL original tool_input fields since
# updatedInput is a full replacement, not a merge. Only the prompt changes.
printf '%s' "$INPUT" | jq --arg injection "$INJECTION" '{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "updatedInput": (.tool_input | .prompt = ($injection + "\n\n" + .prompt))
  }
}'
