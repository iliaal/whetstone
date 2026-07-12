#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
readonly REPO_ROOT
readonly MANIFEST="$REPO_ROOT/plugins/whetstone/.codex-plugin/plugin.json"

command -v codex >/dev/null 2>&1 || {
	printf 'codex is not available on PATH\n' >&2
	exit 1
}

codex plugin marketplace add "$REPO_ROOT"
codex plugin add whetstone@whetstone

expected_version=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$MANIFEST")
plugin_state=$(codex plugin list --marketplace whetstone --json)
installed_version=$(printf '%s' "$plugin_state" | python3 -c '
import json, sys

plugins = json.load(sys.stdin).get("installed", [])
match = next((item for item in plugins if item.get("pluginId") == "whetstone@whetstone"), None)
if not match or not match.get("installed") or not match.get("enabled"):
    raise SystemExit(1)
print(match.get("version", ""))
') || {
	printf 'Whetstone was installed but is not enabled; preserving direct skill fallbacks.\n' >&2
	exit 1
}

if [[ "$installed_version" != "$expected_version" ]]; then
	printf 'Whetstone version mismatch: expected %s, Codex reports %s; preserving direct skill fallbacks.\n' \
		"$expected_version" "$installed_version" >&2
	exit 1
fi

bash "$SCRIPT_DIR/sync-to-tools.sh"
printf 'Whetstone Codex plugin installed and duplicate sources retired. Start a new Codex thread to load it.\n'
