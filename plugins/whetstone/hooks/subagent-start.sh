#!/usr/bin/env bash
set -Eeuo pipefail
exec 2>/dev/null
umask 077
export LC_ALL=C
trap 'rm -f -- "${QUEUE_TEMP:-}" || :; exit 0' EXIT
command -v jq >/dev/null || exit 0
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
# shellcheck source=subagent-queue.sh
source "$SCRIPT_DIR/subagent-queue.sh"

INPUT=$(cat)
queue_open
# A conditional function call suppresses errexit inside it, so call it directly.
queue_claim
# shellcheck source=match-skills.sh
source "$SCRIPT_DIR/match-skills.sh"
