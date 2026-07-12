#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
readonly REPO_ROOT
readonly MANIFEST="$REPO_ROOT/plugins/whetstone/.codex-plugin/plugin.json"
readonly CODEX_HOME_DIR="${CODEX_HOME:-$HOME/.codex}"
readonly CACHEBUSTER_HELPER="$CODEX_HOME_DIR/skills/.system/plugin-creator/scripts/update_plugin_cachebuster.py"

backup=$(mktemp)
mutated_hash=""
restored=false
cp --preserve=all "$MANIFEST" "$backup"

restore_manifest() {
	local current_hash
	[[ "$restored" == false ]] || return 0
	if [[ -n "$mutated_hash" ]]; then
		current_hash=$(sha256sum "$MANIFEST" | awk '{print $1}')
		if [[ "$current_hash" != "$mutated_hash" ]]; then
			printf 'Refusing to overwrite a concurrent manifest edit; original saved at %s\n' "$backup" >&2
			return 1
		fi
	fi
	cp --preserve=all "$backup" "$MANIFEST"
	rm -f -- "$backup"
	restored=true
}

trap restore_manifest EXIT

[[ -f "$CACHEBUSTER_HELPER" ]] || {
	printf 'Codex plugin cachebuster helper not found: %s\n' "$CACHEBUSTER_HELPER" >&2
	exit 1
}
command -v codex >/dev/null 2>&1 || {
	printf 'codex is not available on PATH\n' >&2
	exit 1
}

python3 "$CACHEBUSTER_HELPER" "$REPO_ROOT/plugins/whetstone"
mutated_hash=$(sha256sum "$MANIFEST" | awk '{print $1}')
bash "$SCRIPT_DIR/install-codex-plugin.sh"
restore_manifest
trap - EXIT

printf 'Whetstone Codex plugin refreshed. Start a new Codex thread to load it.\n'
