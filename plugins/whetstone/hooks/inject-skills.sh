#!/usr/bin/env bash
set -Eeuo pipefail
exec >/dev/null 2>&1
umask 077
export LC_ALL=C

# Recording must never affect the tool's permission flow, even on internal errors.
trap 'rm -f -- "${QUEUE_TEMP:-}" || :; exit 0' EXIT
command -v jq >/dev/null || exit 0
command -v flock >/dev/null || exit 0
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
# shellcheck source=subagent-queue.sh
source "$SCRIPT_DIR/subagent-queue.sh"

INPUT=$(cat)
queue_open
printf '%s' "$INPUT" | jq -e '
  (.tool_use_id | type == "string" and test("^[A-Za-z0-9][A-Za-z0-9._-]{0,127}\\z")) and
  (.tool_input | type == "object") and
  (.tool_input.prompt | type == "string") and
  ((.tool_input.subagent_type // "general-purpose") | type == "string")
' >/dev/null
TOOL_USE_ID=$(printf '%s' "$INPUT" | jq -r '.tool_use_id')

QUEUE_TEMP=$(mktemp "$QUEUE_DIR/.pending-XXXXXXXX")
printf '%s' "$INPUT" | jq '{
  subagent_type: ((.tool_input.subagent_type // "general-purpose") | sub("^whetstone:"; "")),
  prompt: .tool_input.prompt,
  enqueued_at: (now | floor)
}' >"$QUEUE_TEMP"
# Serialize publication and cap enforcement; readers only see complete JSON files.
exec 9>"$QUEUE_DIR/.lock"
flock -w 4 9
STAMP=$(date +%s%N)
[[ "$STAMP" =~ ^[0-9]{19}$ ]]
mv -T -- "$QUEUE_TEMP" "$QUEUE_DIR/$STAMP-$TOOL_USE_ID.json"
QUEUE_TEMP=
queue_cap
