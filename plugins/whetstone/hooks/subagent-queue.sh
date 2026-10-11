#!/usr/bin/env bash

queue_open() {
  local session_id dir cutoff
  session_id=$(printf '%s' "$INPUT" | jq -er '
    .session_id | select(type == "string" and test("^[A-Za-z0-9][A-Za-z0-9._-]{0,127}\\z"))
  ')
  QUEUE_ROOT="${TMPDIR:-/tmp}/whetstone-subagent-queue-$UID"
  QUEUE_DIR="$QUEUE_ROOT/$session_id"
  for dir in "$QUEUE_ROOT" "$QUEUE_DIR"; do
    if [[ ! -e "$dir" && ! -L "$dir" ]]; then
      mkdir -m 700 -- "$dir" || [[ -d "$dir" ]]
    fi
    [[ -d "$dir" && ! -L "$dir" && -O "$dir" ]]
    [[ $(stat -c '%a' -- "$dir") == 700 ]]
  done
  cutoff=$(($(date +%s) - 900))
  # Sweep abandoned sessions too. Keep lock inodes stable while writers may hold them.
  find "$QUEUE_ROOT" -ignore_readdir_race -mindepth 2 -maxdepth 2 -type f \
    \( -name '*.json' -o -name '.pending-*' \) \
    ! -newermt "@$cutoff" -delete
}

queue_cap() {
  local entries=() entry excess
  shopt -s nullglob
  entries=("$QUEUE_DIR/"*.json)
  excess=$((${#entries[@]} - 64))
  for entry in "${entries[@]}"; do
    ((excess > 0)) || break
    rm -f -- "$entry"
    excess=$((excess - 1))
  done
}

queue_claim() {
  local agent_type entry entry_type claimed
  agent_type=$(printf '%s' "$INPUT" | jq -er '
    .agent_type | select(type == "string" and length > 0) | sub("^whetstone:"; "")
  ')
  shopt -s nullglob
  for entry in "$QUEUE_DIR/"*.json; do
    [[ -f "$entry" && ! -L "$entry" ]] || continue
    entry_type=$(jq -er '.subagent_type | select(type == "string")' "$entry") || continue
    [[ "$entry_type" == "$agent_type" ]] || continue
    claimed="$QUEUE_DIR/.claimed-$$-${entry##*/}"
    # Unique destinations ensure only the process that renames the source owns it.
    if mv -T -- "$entry" "$claimed"; then
      QUEUE_TEMP=$claimed
      INPUT=$(jq '{tool_input: {prompt: .prompt, subagent_type: .subagent_type}}' "$claimed")
      rm -f -- "$claimed"
      QUEUE_TEMP=
      return 0
    fi
  done
  return 1
}
