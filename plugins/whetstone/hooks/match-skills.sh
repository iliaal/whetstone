#!/usr/bin/env bash
# Sourced by subagent-start.sh after claiming a prompt; INPUT retains Jev's input shape.
AGENT_TYPE=$(printf '%s' "$INPUT" | jq -r '.tool_input.subagent_type // empty')

# Skip agent types that can't read files
case "$AGENT_TYPE" in
  Bash | statusline-setup) exit 0 ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=skill-matcher.sh
source "$SCRIPT_DIR/skill-matcher.sh"
$SKILL_PATTERNS_LOADED || exit 0

# One line per prompt: "S" followed by the matches stored when the call was recorded, or
# "L <index>" for a record written before matches were stored. A batch carries every
# prompt of an ambiguous same-type group (see queue_claim).
mapfile -t ENTRIES < <(printf '%s' "$INPUT" | jq -r '
  .tool_input
  | if (.prompts | type) == "array"
    then [.prompts, (.skills | if type == "array" then . else [] end)]
    else [[.prompt], [.skills]] end
  | . as [$prompts, $skills]
  | range(0; $prompts | length)
  | if ($skills[.] | type) == "array"
    then "S" + ([$skills[.][] | strings | " " + .] | join(""))
    else "L \(.)" end
')

prompt_at() {
  printf '%s' "$INPUT" | jq -r --argjson i "$1" '
    .tool_input | if (.prompts | type) == "array" then .prompts[$i] else .prompt end | strings
  '
}

add_match() {
  [[ " ${ALL_MATCHES[*]-} " == *" $1 "* ]] || ALL_MATCHES+=("$1")
}

# A batch suggests the union of every prompt's matches, so each start still receives
# its own skills; the recipient filters the rest by applicability.
ALL_MATCHES=()
for entry in ${ENTRIES[@]+"${ENTRIES[@]}"}; do
  if [[ "$entry" == S* ]]; then
    read -ra STORED <<<"${entry#S}"
    for skill_name in ${STORED[@]+"${STORED[@]}"}; do
      if skill_installed "$skill_name"; then
        add_match "$skill_name"
      fi
    done
    continue
  fi
  prompt=$(prompt_at "${entry#L }")
  [[ -n "${prompt//[[:space:]]/}" ]] || continue
  match_prompt "$prompt"
  for skill_name in ${PROMPT_MATCHES[@]+"${PROMPT_MATCHES[@]}"}; do
    add_match "$skill_name"
  done
done
REGEX_MATCH_COUNT=${#ALL_MATCHES[@]}

if [[ "${WHETSTONE_JEV:-}" == 1 && ${#ENTRIES[@]} -eq 1 && ${#ALL_MATCHES[@]} -lt $MAX_SKILLS ]] &&
  PROMPT=$(prompt_at 0) && [[ -n "${PROMPT//[[:space:]]/}" ]] &&
  command -v python3 >/dev/null 2>&1 && command -v "${WHETSTONE_JEV_COMMAND:-jev}" >/dev/null 2>&1; then
  prompt_context "$PROMPT"
  ELIGIBLE=()
  for skill_name in "${SKILL_NAMES[@]}"; do
    [[ -f "$PLUGIN_ROOT/skills/$skill_name/SKILL.md" ]] || continue
    [[ " ${ALL_MATCHES[*]-} " == *" $skill_name "* ]] && continue
    if [[ -n "${SKILL_NEGATIVE[$skill_name]+x}" ]] &&
      grep -qE "${SKILL_NEGATIVE[$skill_name]}" <<<"$PROMPT_LOWER" 2>/dev/null; then
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

INJECTION="BEFORE STARTING: These skill files matched your task description; confirm each applies to your actual task, then read and follow it:"
if [[ ${#ENTRIES[@]} -gt 1 ]]; then
  INJECTION="BEFORE STARTING: Several tasks of this agent type started together, so these skill files matched one or more of them, not necessarily yours. Confirm each applies to your actual task; read and follow only those that do:"
elif [[ $REGEX_MATCH_COUNT -eq 0 ]]; then
  INJECTION="BEFORE STARTING: Jev suggests these skill files for your task; confirm each applies to your actual task before following it:"
fi
for index in "${!ALL_MATCHES[@]}"; do
  skill_name="${ALL_MATCHES[$index]}"
  if [[ $index -eq $REGEX_MATCH_COUNT && $index -gt 0 ]]; then
    INJECTION="$INJECTION
Additional skill suggestions (Jev; check applicability against your actual task before following):"
  fi
  INJECTION="$INJECTION
- ${PLUGIN_ROOT}/skills/${skill_name}/SKILL.md"
done
INJECTION="$INJECTION
If you cannot read the files, proceed with your best judgment."

printf '%s' "$INJECTION" | jq -Rs '{
  "hookSpecificOutput": {
    "hookEventName": "SubagentStart",
    "additionalContext": .[:8000]
  }
}'
