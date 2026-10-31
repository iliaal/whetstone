#!/usr/bin/env bash
# Sourced at top level (skill-patterns.sh declares its arrays with plain `declare -A`,
# which a function-scoped source would make local). Sets SKILL_PATTERNS_LOADED.
SKILL_MATCHER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SKILL_MATCHER_DIR/.." && pwd)"
MAX_SKILLS=5
SKILL_PATTERNS_LOADED=false
SKILL_NAMES=()

if [[ -f "$SKILL_MATCHER_DIR/skill-patterns.sh" ]]; then
  # shellcheck source=skill-patterns.sh
  source "$SKILL_MATCHER_DIR/skill-patterns.sh"

  # Guard: older pattern files may not declare SKILL_MAINT_SUPPRESS
  if ! declare -p SKILL_MAINT_SUPPRESS &>/dev/null; then
    declare -A SKILL_MAINT_SUPPRESS
  fi

  # Guard: older pattern files may not declare SKILL_NEGATIVE
  if ! declare -p SKILL_NEGATIVE &>/dev/null; then
    declare -A SKILL_NEGATIVE
  fi

  readarray -t SKILL_NAMES < <(printf '%s\n' "${!SKILL_PATTERNS[@]}" | LC_ALL=C sort)
  # shellcheck disable=SC2034 # read by the sourcing hook
  SKILL_PATTERNS_LOADED=true
fi

# Sets PROMPT_HAYSTACK and IS_MAINT_CONTEXT for one prompt.
prompt_context() {
  local prompt=$1 lower flat

  # Detect plugin-maintenance context. When the prompt mentions plugin internals,
  # skill files, or maintenance commands, skills whose names appear as references
  # shouldn't fire as if the user is invoking them. Stays line-based: every marker
  # fits on one line, and `^run` means "a line that starts with run".
  IS_MAINT_CONTEXT=false
  if grep -qiE 'plugins/whetstone/(skills|agents|commands)/|skill-patterns\.sh|/sync-from-repos\b|/audit-plugin\b|/(analyze-misfires|diagnose-negatives|evolve-skill|eval-skills)\b|^run .{0,80}distiller\.py +(analyze-misfires|diagnose-negatives)\b' <<<"$prompt" 2>/dev/null; then
    IS_MAINT_CONTEXT=true
  fi

  # Lowercase prompt for case-insensitive matching
  lower=$(printf '%s' "$prompt" | tr '[:upper:]' '[:lower:]')

  # grep matches line by line, so keywords split by a newline (a request followed by
  # pasted code, logs, or a diff) never match a `.{0,N}` span. Append the whole prompt
  # as one extra line with each whitespace run collapsed to a single space. The
  # original lines stay in the input because some patterns use `^`/`$` as line
  # boundaries ("add unit tests" ending a line above a code block).
  flat=$(printf '%s' "$lower" | tr -s '\t\n\r\v\f ' ' ')
  PROMPT_HAYSTACK="$lower"$'\n'"$flat"
  return 0
}

# True when an ERE matches any line of the current prompt or its flattened copy.
prompt_matches() {
  grep -qE "$1" <<<"$PROMPT_HAYSTACK" 2>/dev/null
}

# A skill name is usable only when it is a known pattern key with an installed SKILL.md.
skill_installed() {
  [[ "$1" =~ ^[a-z0-9][a-z0-9-]*$ && -n "${SKILL_PATTERNS[$1]+x}" && -f "$PLUGIN_ROOT/skills/$1/SKILL.md" ]]
}

# Sets PROMPT_HAYSTACK, IS_MAINT_CONTEXT, and PROMPT_MATCHES (tier-ordered, capped) for one prompt.
match_prompt() {
  local prompt=$1 skill_name pattern skill_path tier
  local tier1=() tier2=() tier3=()

  prompt_context "$prompt"

  for skill_name in "${SKILL_NAMES[@]}"; do
    pattern="${SKILL_PATTERNS[$skill_name]}"
    if prompt_matches "$pattern"; then
      skill_path="$PLUGIN_ROOT/skills/$skill_name/SKILL.md"
      [[ -f "$skill_path" ]] || continue

      # Suppress when the prompt carries an explicit marker for a NEIGHBOURING language
      # or stack. SKILL_PATTERNS cannot express "X unless Y" (ERE has no lookahead), so
      # a language-neutral alternative like `segfault` or `\.h\b` otherwise fires the C
      # skill on a C# or Objective-C prompt. Keep entries to unambiguous markers; this is
      # not a place to fix a positive pattern that is merely too loose.
      if [[ -n "${SKILL_NEGATIVE[$skill_name]+x}" ]]; then
        if prompt_matches "${SKILL_NEGATIVE[$skill_name]}"; then
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
        1) tier1+=("$skill_name") ;;
        2) tier2+=("$skill_name") ;;
        3) tier3+=("$skill_name") ;;
      esac
    fi
  done

  PROMPT_MATCHES=()
  [[ ${#tier1[@]} -gt 0 ]] && PROMPT_MATCHES+=("${tier1[@]}")
  [[ ${#tier2[@]} -gt 0 ]] && PROMPT_MATCHES+=("${tier2[@]}")
  [[ ${#tier3[@]} -gt 0 ]] && PROMPT_MATCHES+=("${tier3[@]}")

  # Cap at 5 skills per prompt to avoid context bloat
  if [[ ${#PROMPT_MATCHES[@]} -gt $MAX_SKILLS ]]; then
    PROMPT_MATCHES=("${PROMPT_MATCHES[@]:0:$MAX_SKILLS}")
  fi
  return 0
}
