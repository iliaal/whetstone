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

queue_lock() {
  command -v flock >/dev/null || return 1
  exec 9>"$QUEUE_DIR/.lock"
  flock -w 4 9
}

queue_claim() {
  local agent_type
  agent_type=$(printf '%s' "$INPUT" | jq -er '
    .agent_type | select(type == "string" and length > 0) | sub("^whetstone:"; "")
  ')
  # Serialize with recorders, discarders, and other claimers so the pending count stays exact.
  queue_lock
  # Errexit ends the hook on a failed claim; on success, release before matching runs.
  queue_claim_locked "$agent_type"
  exec 9>&-
}

# Prints alternating lines: record path, then the record's {prompt, skills} as one JSON
# line. Reading each record once, in the same pass that selects it, tolerates a record
# that the unlocked stale-entry sweep removes mid-claim: jq reports the missing file and
# continues with the rest.
queue_select() {
  local agent_type=$1 entry candidates=()
  shift
  for entry in "$@"; do
    [[ -f "$entry" && ! -L "$entry" ]] && candidates+=("$entry")
  done
  ((${#candidates[@]} > 0)) || return 0
  jq -r --arg type "$agent_type" '
    objects | select(.subagent_type == $type)
    | input_filename, ({prompt, skills} | tojson)
  ' -- "${candidates[@]}" || :
}

queue_claim_locked() {
  local agent_type=$1 index pending=() used=() records=()
  local selected=()
  shopt -s nullglob
  # One jq pass per group keeps the lock hold short; record names are [0-9A-Za-z._-] only.
  mapfile -t selected < <(queue_select "$agent_type" "$QUEUE_DIR/".used-*.json)
  for ((index = 0; index + 1 < ${#selected[@]}; index += 2)); do
    used+=("${selected[index]}")
    records+=("${selected[index + 1]}")
  done
  mapfile -t selected < <(queue_select "$agent_type" "$QUEUE_DIR/"*.json)
  for ((index = 0; index + 1 < ${#selected[@]}; index += 2)); do
    pending+=("${selected[index]}")
    records+=("${selected[index + 1]}")
  done
  if ((${#pending[@]} == 0)); then
    ((${#used[@]} == 0)) || rm -f -- "${used[@]}"
    return 1
  fi
  if ((${#pending[@]} == 1 && ${#used[@]} == 0)); then
    rm -f -- "${pending[0]}"
    INPUT=$(jq --arg type "$agent_type" '{tool_input: (. + {subagent_type: $type})}' <<<"${records[0]}")
    return 0
  fi
  # SubagentStart carries no tool-call ID or prompt, so overlapping same-type starts
  # cannot be matched to their records. Each start in the group gets every group
  # prompt; used records stay until the group's last pending record is claimed.
  INPUT=$(printf '%s\n' "${records[@]}" | jq -s --arg type "$agent_type" '
    {tool_input: {prompts: map(.prompt), skills: map(.skills), subagent_type: $type}}
  ')
  if ((${#pending[@]} == 1)); then
    rm -f -- "${used[@]}" "${pending[0]}"
  else
    # A record the stale sweep already removed has nothing left to mark.
    mv -T -- "${pending[0]}" "$QUEUE_DIR/.used-${pending[0]##*/}" || :
  fi
  return 0
}

queue_discard() {
  local tool_use_id entry name
  tool_use_id=$(jq -er '
    .tool_use_id | select(type == "string" and test("^[A-Za-z0-9][A-Za-z0-9._-]{0,127}\\z"))
  ' <<<"${INPUT}")
  # Without the lock, a deletion could interleave with a claim's selection and removal.
  queue_lock
  shopt -s nullglob
  for entry in "${QUEUE_DIR}/"*.json; do
    [[ -f "${entry}" && ! -L "${entry}" ]] || continue
    name=${entry##*/}
    [[ "${name#*-}" == "${tool_use_id}.json" ]] || continue
    rm -f -- "${entry}"
  done
  exec 9>&-
}
