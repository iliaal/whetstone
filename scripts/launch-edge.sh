#!/usr/bin/env bash
# Launch Edge with a dedicated compound-engineering profile and CDP debug port.
#
# Profile lives on the Windows side (C:\Users\ilia\edge-compound-engineering)
# so Edge reads/writes locally rather than across the WSL 9P bridge.
#
# Close all Edge windows before first launch -- Edge ignores
# --remote-debugging-port when another instance is already running.
set -euo pipefail

EDGE='/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
PORT=9225
PROFILE='C:\Users\ilia\edge-compound-engineering'

if [[ ! -x "$EDGE" ]]; then
    echo "Error: msedge.exe not found at: $EDGE" >&2
    exit 1
fi

"$EDGE" \
    --remote-debugging-port="$PORT" \
    --remote-debugging-address=0.0.0.0 \
    --remote-allow-origins=* \
    --user-data-dir="$PROFILE" \
    >/dev/null 2>&1 &

echo "Edge launched on CDP port $PORT (profile: $PROFILE)"
echo "First run: log in to X, then drafts will reuse the session."
