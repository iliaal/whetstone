#!/usr/bin/env bash
set -Eeuo pipefail
exec >/dev/null 2>&1
umask 077
export LC_ALL=C
trap 'exit 0' EXIT
command -v jq >/dev/null || exit 0
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
# shellcheck source=subagent-queue.sh
source "${SCRIPT_DIR}/subagent-queue.sh"

INPUT=$(cat)
jq -e '
  (.hook_event_name == "PostToolUseFailure" or .hook_event_name == "PermissionDenied") and
  (.tool_name == "Task" or .tool_name == "Agent")
' <<<"${INPUT}" >/dev/null
queue_open
queue_discard
