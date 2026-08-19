#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
readonly REPO_ROOT

test_manifest_parity() {
	local claude_version codex_version marketplace_version explicit_only_actual explicit_only_expected
	claude_version=$(jq -r '.version' "$REPO_ROOT/plugins/whetstone/.claude-plugin/plugin.json")
	codex_version=$(jq -r '.version' "$REPO_ROOT/plugins/whetstone/.codex-plugin/plugin.json")
	marketplace_version=$(jq -r '.plugins[0].version' "$REPO_ROOT/.claude-plugin/marketplace.json")

	[[ "$claude_version" == "$codex_version" ]]
	[[ "$claude_version" == "$marketplace_version" ]]

	diff -u \
		<(jq -S '.mcpServers' "$REPO_ROOT/plugins/whetstone/.claude-plugin/plugin.json") \
		<(jq -S '.mcpServers' "$REPO_ROOT/plugins/whetstone/.mcp.json")

	jq -e '
    .name == "whetstone" and
    .plugins == [{
      "name": "whetstone",
      "source": {"source": "local", "path": "./plugins/whetstone"},
      "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
      "category": "Productivity"
    }]
  ' "$REPO_ROOT/.agents/plugins/marketplace.json" >/dev/null

	for skill in ia-compound-docs ia-file-todos; do
		grep -q '^disable-model-invocation: true$' "$REPO_ROOT/plugins/whetstone/skills/$skill/SKILL.md"
		grep -q '^  allow_implicit_invocation: false$' "$REPO_ROOT/plugins/whetstone/skills/$skill/agents/openai.yaml"
	done

	explicit_only_actual=$(grep -rl '^disable-model-invocation: true$' "$REPO_ROOT/plugins/whetstone/skills" --include=SKILL.md | sort)
	explicit_only_expected=$(printf '%s\n' \
		"$REPO_ROOT/plugins/whetstone/skills/ia-compound-docs/SKILL.md" \
		"$REPO_ROOT/plugins/whetstone/skills/ia-file-todos/SKILL.md")
	[[ "$explicit_only_actual" == "$explicit_only_expected" ]]
}

# Codex >= 0.147 picks a manifest by looking for a root plugin.json carrying the
# Agent Plugins $schema, in preference to .codex-plugin/plugin.json. Skills loaded
# through that path are truncated to a byte budget with no install-time error, so
# the model proceeds on a half-read SKILL.md. Adding that field for "interoperability"
# is a one-line change with a silent, majority-of-skills blast radius, so assert its
# absence unconditionally rather than behind a predicate.
test_no_agent_plugins_schema_in_root_manifest() {
	local hits over_budget total
	if [[ -f "$REPO_ROOT/plugin.json" ]]; then
		printf 'FAIL: a root plugin.json exists; Codex prefers it over .codex-plugin/plugin.json\n' >&2
		return 1
	fi
	# Test the $schema key specifically. A bare substring match over the file would
	# false-FAIL on a homepage or keywords entry mentioning agent-plugins, and this
	# function is a blocking release gate.
	hits=""
	while IFS= read -r manifest; do
		if ! jq -e . "$manifest" >/dev/null 2>&1; then
			printf 'FAIL: %s is not valid JSON; cannot rule out an Agent Plugins $schema\n' "$manifest" >&2
			return 1
		fi
		# A $schema that is present but not a string is malformed: Codex's routing
		# behavior on it is unknown, so a blocking gate has to fail closed rather
		# than read "not a string" as "not a reroute".
		if jq -e 'has("$schema") and (.["$schema"] | type != "string")' "$manifest" >/dev/null 2>&1; then
			printf 'FAIL: %s has a non-string $schema; cannot rule out an Agent Plugins reroute\n' "$manifest" >&2
			return 1
		fi
		if jq -e '(.["$schema"] // "") | test("agent-plugins")' "$manifest" >/dev/null 2>&1; then
			hits+="$manifest"$'\n'
		fi
	done < <(find "$REPO_ROOT/.claude-plugin" "$REPO_ROOT/plugins/whetstone/.claude-plugin" \
		"$REPO_ROOT/plugins/whetstone/.codex-plugin" -name 'plugin.json' 2>/dev/null)
	if [[ -n "$hits" ]]; then
		printf 'FAIL: Agent Plugins $schema found in a manifest, which reroutes Codex skill loading:\n%s' "$hits" >&2
		return 1
	fi

	# Advisory, not a gate: the budget is the host's, and shrinking 20-odd skills is a
	# separate decision. Printing the count keeps it from being discovered by a user.
	over_budget=0
	total=0
	for skill in "$REPO_ROOT"/plugins/whetstone/skills/*/SKILL.md; do
		total=$((total + 1))
		if [[ $(wc -c <"$skill") -gt 8000 ]]; then
			over_budget=$((over_budget + 1))
		fi
	done
	if ((over_budget > 0)); then
		printf 'NOTE: %d/%d skills exceed the 8000-byte Codex skill-prompt budget; they truncate silently if a root manifest ever reroutes loading\n' \
			"$over_budget" "$total"
	fi
}

test_sync_migrates_legacy_codex_links() {
	local tmp unrelated_target fake_bin
	tmp=$(mktemp -d)
	unrelated_target="$tmp/unrelated-skill"
	fake_bin="$tmp/bin"
	mkdir -p "$tmp/.codex/skills" "$unrelated_target" "$fake_bin"
	cat >"$fake_bin/codex" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "plugin list" && -n "${WHETSTONE_FAKE_STATUS:-}" ]]; then
  printf 'whetstone@whetstone  installed, %s  4.2.1  /fixture\n' "$WHETSTONE_FAKE_STATUS"
fi
EOF
	chmod +x "$fake_bin/codex"
	ln -s "$REPO_ROOT/plugins/whetstone/skills/ia-debugging" "$tmp/.codex/skills/ia-debugging"
	ln -s "$unrelated_target" "$tmp/.codex/skills/unrelated"

	HOME="$tmp" CODEX_HOME="$tmp/.codex" WHETSTONE_FAKE_STATUS=enabled PATH="$fake_bin:$PATH" \
		bash "$REPO_ROOT/scripts/sync-to-tools.sh" >/dev/null

	[[ ! -e "$tmp/.codex/skills/ia-debugging" ]]
	[[ -L "$tmp/.codex/skills/unrelated" ]]
	[[ -L "$tmp/.agents/skills/ia-debugging" ]]
	[[ -L "$tmp/.kilocode/skills/ia-debugging" ]]

	ln -s "$REPO_ROOT/plugins/whetstone/skills/ia-debugging" "$tmp/.codex/skills/ia-debugging"
	HOME="$tmp" CODEX_HOME="$tmp/.codex" PATH="$fake_bin:$PATH" \
		bash "$REPO_ROOT/scripts/sync-to-tools.sh" >/dev/null
	[[ -L "$tmp/.codex/skills/ia-debugging" ]]
	if grep -q '^# BEGIN WHETSTONE CODEX SKILL SOURCE EXCLUSIONS$' "$tmp/.codex/config.toml"; then
		printf 'disabled plugin left direct skill sources excluded\n' >&2
		return 1
	fi

	HOME="$tmp" CODEX_HOME="$tmp/.codex" WHETSTONE_FAKE_STATUS=disabled PATH="$fake_bin:$PATH" \
		bash "$REPO_ROOT/scripts/sync-to-tools.sh" >/dev/null
	[[ -L "$tmp/.codex/skills/ia-debugging" ]]
	rm -rf -- "$tmp"
}

test_codex_source_exclusions_are_idempotent() {
	local tmp config first_hash second_hash corrupt_before symlink_home symlink_target
	tmp=$(mktemp -d)
	config="$tmp/config.toml"
	printf 'model = "gpt-5"\n' >"$config"

	python3 "$REPO_ROOT/scripts/configure-codex-skill-sources.py" --codex-home "$tmp" >/dev/null
	first_hash=$(sha256sum "$config" | awk '{print $1}')
	python3 "$REPO_ROOT/scripts/configure-codex-skill-sources.py" --codex-home "$tmp" >/dev/null
	second_hash=$(sha256sum "$config" | awk '{print $1}')

	[[ "$first_hash" == "$second_hash" ]]
	# Derived, never hardcoded: this assertion is about one entry per shipped
	# skill, so a literal here silently rots on the next skill added.
	local expected_skill_sources
	expected_skill_sources=$(find "$REPO_ROOT/plugins/whetstone/skills" -mindepth 1 -maxdepth 1 -type d | wc -l)
	[[ "$(grep -c '^\[\[skills.config\]\]$' "$config")" -eq "$expected_skill_sources" ]]
	[[ "$(grep -c '^model = "gpt-5"$' "$config")" -eq 1 ]]
	python3 -c 'import pathlib, sys, tomllib; tomllib.loads(pathlib.Path(sys.argv[1]).read_text())' "$config"

	printf '%s\n' 'model = "gpt-5"' '# BEGIN WHETSTONE CODEX SKILL SOURCE EXCLUSIONS' >"$config"
	corrupt_before=$(sha256sum "$config" | awk '{print $1}')
	if python3 "$REPO_ROOT/scripts/configure-codex-skill-sources.py" --codex-home "$tmp" >/dev/null 2>&1; then
		printf 'config helper accepted an incomplete managed block\n' >&2
		return 1
	fi
	[[ "$corrupt_before" == "$(sha256sum "$config" | awk '{print $1}')" ]]

	symlink_home="$tmp/symlink-home"
	symlink_target="$tmp/dotfiles-codex.toml"
	mkdir -p "$symlink_home"
	printf 'model = "gpt-5"\n' >"$symlink_target"
	ln -s "$symlink_target" "$symlink_home/config.toml"
	python3 "$REPO_ROOT/scripts/configure-codex-skill-sources.py" --codex-home "$symlink_home" >/dev/null
	[[ -L "$symlink_home/config.toml" ]]
	grep -q '^# BEGIN WHETSTONE CODEX SKILL SOURCE EXCLUSIONS$' "$symlink_target"
	python3 "$REPO_ROOT/scripts/configure-codex-skill-sources.py" --codex-home "$symlink_home" --remove >/dev/null
	[[ -L "$symlink_home/config.toml" ]]
	if grep -q '^# BEGIN WHETSTONE CODEX SKILL SOURCE EXCLUSIONS$' "$symlink_target"; then
		printf 'managed source exclusions were not removed\n' >&2
		return 1
	fi
	rm -rf -- "$tmp"
}

test_development_refresh_restores_manifest() {
	local tmp work fake_bin helper manifest before_hash after_hash calls sync_calls fake_version
	tmp=$(mktemp -d)
	work="$tmp/work"
	fake_bin="$tmp/bin"
	helper="$tmp/home/.codex/skills/.system/plugin-creator/scripts/update_plugin_cachebuster.py"
	manifest="$work/plugins/whetstone/.codex-plugin/plugin.json"
	calls="$tmp/codex-calls"
	sync_calls="$tmp/sync-calls"
	mkdir -p "$work/scripts" "$(dirname "$manifest")" "$fake_bin" "$(dirname "$helper")"
	cp "$REPO_ROOT/scripts/refresh-codex-plugin.sh" "$work/scripts/refresh-codex-plugin.sh"
	cp "$REPO_ROOT/scripts/install-codex-plugin.sh" "$work/scripts/install-codex-plugin.sh"
	printf '%s\n' '#!/usr/bin/env bash' "printf \"sync\\n\" >>\"\$SYNC_CALLS_FILE\"" >"$work/scripts/sync-to-tools.sh"
	cp "$REPO_ROOT/plugins/whetstone/.codex-plugin/plugin.json" "$manifest"
	# Match what the cachebuster helper produces (<base>+codex.fixture) so the fake
	# codex reports the same version the refreshed manifest carries, at any release.
	fake_version="$(jq -r '.version' "$manifest" | cut -d'+' -f1)+codex.fixture"
	cat >"$helper" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1]) / ".codex-plugin" / "plugin.json"
data = json.loads(path.read_text())
data["version"] = data["version"].split("+", 1)[0] + "+codex.fixture"
path.write_text(json.dumps(data, indent=2) + "\n")
PY
	cat >"$fake_bin/codex" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$CODEX_CALLS_FILE"
if [[ "$*" == "plugin list" ]]; then
  printf 'whetstone@whetstone  installed, enabled  4.2.1  /fixture\n'
fi
if [[ "$*" == "plugin list --marketplace whetstone --json" ]]; then
  printf '{"installed":[{"pluginId":"whetstone@whetstone","version":"%s","installed":true,"enabled":true}]}\n' "$WHETSTONE_FAKE_VERSION"
fi
EOF
	chmod +x "$fake_bin/codex"

	before_hash=$(sha256sum "$manifest" | awk '{print $1}')
	CODEX_CALLS_FILE="$calls" SYNC_CALLS_FILE="$sync_calls" WHETSTONE_FAKE_VERSION="$fake_version" CODEX_HOME="$tmp/home/.codex" PATH="$fake_bin:$PATH" \
		bash "$work/scripts/refresh-codex-plugin.sh" >/dev/null
	after_hash=$(sha256sum "$manifest" | awk '{print $1}')

	[[ "$before_hash" == "$after_hash" ]]
	[[ "$(grep -Fxc "plugin marketplace add $work" "$calls")" -eq 1 ]]
	[[ "$(grep -Fxc 'plugin add whetstone@whetstone' "$calls")" -eq 1 ]]
	[[ "$(wc -l <"$sync_calls")" -eq 1 ]]

	if CODEX_CALLS_FILE="$calls" SYNC_CALLS_FILE="$sync_calls" WHETSTONE_FAKE_VERSION='0.0.1' CODEX_HOME="$tmp/home/.codex" PATH="$fake_bin:$PATH" \
		bash "$work/scripts/install-codex-plugin.sh" >/dev/null 2>&1; then
		printf 'Codex installer accepted a stale installed version\n' >&2
		return 1
	fi
	[[ "$(wc -l <"$sync_calls")" -eq 1 ]]
	rm -rf -- "$tmp"
}

write_fixture_files() {
	mkdir -p \
		.agents/plugins \
		.claude-plugin \
		distillery/scripts \
		distillery/tests \
		plugins/whetstone/.claude-plugin \
		plugins/whetstone/.codex-plugin \
		plugins/whetstone/skills/ia-debugging \
		scripts

	cp "$REPO_ROOT/scripts/release.sh" scripts/release.sh
	cp "$REPO_ROOT/scripts/install-codex-plugin.sh" scripts/install-codex-plugin.sh
	cp "$REPO_ROOT/scripts/configure-codex-skill-sources.py" scripts/configure-codex-skill-sources.py
	printf '#!/usr/bin/env bash\nexit 0\n' >scripts/update-metadata.sh
	printf '#!/usr/bin/env bash\nexit 0\n' >scripts/mirror-to-ai-skills.sh
	printf '#!/usr/bin/env bash\nexit 0\n' >scripts/publish-clawhub.sh
	printf '%s\n' '#!/usr/bin/env bash' "python3 \"\$(dirname \"\$0\")/configure-codex-skill-sources.py\" >/dev/null" >scripts/sync-to-tools.sh
	printf '#!/usr/bin/env bash\nexit 0\n' >scripts/update-plugin.sh
	printf '#!/usr/bin/env bash\nexit 0\n' >scripts/test-codex-plugin.sh
	chmod +x scripts/*.sh

	printf 'raise SystemExit(0)\n' >distillery/scripts/distiller.py
	printf 'raise SystemExit(0)\n' >scripts/generate-manifest.py
	printf '{}\n' >distillery/.skill-versions.json
	printf 'fixture\n' >distillery/tests/fixture.txt
	printf '%s\n' '---' 'name: ia-debugging' 'description: Debug failures.' '---' >plugins/whetstone/skills/ia-debugging/SKILL.md

	printf '%s\n' \
		'{"plugins":[{"version":"4.2.1"}]}' >.claude-plugin/marketplace.json
	printf '%s\n' \
		'{"name":"whetstone","version":"4.2.1","description":"fixture"}' >plugins/whetstone/.claude-plugin/plugin.json
	printf '%s\n' \
		'{"name":"whetstone","version":"4.2.1","description":"fixture"}' >plugins/whetstone/.codex-plugin/plugin.json
	printf '%s\n' '{"mcpServers":{}}' >plugins/whetstone/.mcp.json
	printf '%s\n' \
		'{"name":"whetstone","interface":{"displayName":"Before"},"plugins":[{"name":"whetstone","source":{"source":"local","path":"./plugins/whetstone"},"policy":{"installation":"AVAILABLE","authentication":"ON_INSTALL"},"category":"Productivity"}]}' \
		>.agents/plugins/marketplace.json
	printf '# Fixture\n' >README.md
	printf '%s\n' '# Changelog' '' '## [4.2.1] - 2026-07-12' '' '### Changed' '' "- \`ia-debugging\`: Fixture release." >CHANGELOG.md
}

write_fake_commands() {
	local fake_bin="$1"
	mkdir -p "$fake_bin"

	printf '#!/usr/bin/env bash\nexit 0\n' >"$fake_bin/gh"
	printf '#!/usr/bin/env bash\nexit 1\n' >"$fake_bin/npx"
	cat >"$fake_bin/codex" <<'EOF'
#!/usr/bin/env bash
if [[ "$1" == "plugin" ]]; then
  local_head=$(git rev-parse HEAD)
  remote_head=$(git ls-remote origin refs/heads/master | awk '{print $1}')
  if [[ "$local_head" == "$remote_head" ]]; then
    printf 'Codex refresh ran before commit or after push\n' >&2
    exit 42
  fi
fi
printf '%s\n' "$*" >>"$CODEX_CALLS_FILE"
if [[ "${CODEX_FAIL_ADD:-0}" == "1" && "$*" == "plugin add whetstone@whetstone" ]]; then
  exit 43
fi
if [[ "$*" == "plugin list" ]]; then
  printf 'whetstone@whetstone  installed, enabled  4.2.1  /fixture\n'
fi
if [[ "$*" == "plugin list --marketplace whetstone --json" ]]; then
  printf '{"installed":[{"pluginId":"whetstone@whetstone","version":"4.2.1","installed":true,"enabled":true}]}\n'
fi
EOF
	chmod +x "$fake_bin/gh" "$fake_bin/npx" "$fake_bin/codex"
}

write_no_codex_commands() {
	local fake_bin="$1" command_path name
	mkdir -p "$fake_bin"
	for name in awk bash cut date dirname find git grep head jq mv python3 sed sort tail tr; do
		command_path=$(command -v "$name")
		ln -s "$command_path" "$fake_bin/$name"
	done
	printf '#!/usr/bin/env bash\nexit 0\n' >"$fake_bin/gh"
	printf '#!/usr/bin/env bash\nexit 1\n' >"$fake_bin/npx"
	chmod +x "$fake_bin/gh" "$fake_bin/npx"
}

test_release_refresh_ordering() {
	local tmp origin work fake_bin no_codex_bin codex_calls before_remote after_failure_remote config_hash_before config_hash_after
	tmp=$(mktemp -d)
	origin="$tmp/origin.git"
	work="$tmp/work"
	fake_bin="$tmp/bin"
	no_codex_bin="$tmp/no-codex-bin"
	codex_calls="$tmp/codex-calls"

	git init --bare -q "$origin"
	git init -q -b master "$work"
	cd "$work"
	git config user.email test@example.com
	git config user.name Test
	git remote add origin "$origin"
	write_fixture_files
	git add .
	git commit -q -m initial
	git push -q -u origin master

	mkdir -p "$tmp/home/ai/ai-skills"
	git init --bare -q "$tmp/ai-origin.git"
	git init -q -b master "$tmp/home/ai/ai-skills"
	git -C "$tmp/home/ai/ai-skills" config user.email test@example.com
	git -C "$tmp/home/ai/ai-skills" config user.name Test
	git -C "$tmp/home/ai/ai-skills" remote add origin "$tmp/ai-origin.git"
	printf '# Changelog\n\n## [0.1.0]\n' >"$tmp/home/ai/ai-skills/CHANGELOG.md"
	git -C "$tmp/home/ai/ai-skills" add CHANGELOG.md
	git -C "$tmp/home/ai/ai-skills" commit -q -m initial
	git -C "$tmp/home/ai/ai-skills" push -q -u origin master

	write_fake_commands "$fake_bin"
	write_no_codex_commands "$no_codex_bin"
	python3 - <<'PY'
import json
from pathlib import Path

path = Path('.agents/plugins/marketplace.json')
data = json.loads(path.read_text())
data['interface']['displayName'] = 'After'
path.write_text(json.dumps(data, indent=2) + '\n')
Path('README.md').write_text('# Fixture release\n')
PY

	CODEX_CALLS_FILE="$codex_calls" HOME="$tmp/home" CODEX_HOME="$tmp/home/.codex" PATH="$fake_bin:/usr/bin:/bin" \
		bash scripts/release.sh 'release: fixture' >"$tmp/success.out" 2>&1

	[[ "$(grep -Fxc "plugin marketplace add $work" "$codex_calls")" -eq 1 ]]
	[[ "$(grep -Fxc 'plugin add whetstone@whetstone' "$codex_calls")" -eq 1 ]]
	[[ "$(git show origin/master:.agents/plugins/marketplace.json | jq -r '.interface.displayName')" == "After" ]]

	printf '# Failure candidate\n' >README.md
	before_remote=$(git ls-remote origin refs/heads/master | awk '{print $1}')
	config_hash_before=$(sha256sum "$tmp/home/.codex/config.toml" | awk '{print $1}')
	if CODEX_FAIL_ADD=1 CODEX_CALLS_FILE="$codex_calls" HOME="$tmp/home" CODEX_HOME="$tmp/home/.codex" PATH="$fake_bin:/usr/bin:/bin" \
		bash scripts/release.sh 'release: must not publish' >"$tmp/failure.out" 2>&1; then
		printf 'release unexpectedly succeeded when Codex install failed\n' >&2
		return 1
	fi
	after_failure_remote=$(git ls-remote origin refs/heads/master | awk '{print $1}')
	config_hash_after=$(sha256sum "$tmp/home/.codex/config.toml" | awk '{print $1}')
	[[ "$before_remote" == "$after_failure_remote" ]]
	[[ "$config_hash_before" == "$config_hash_after" ]]

	printf '# No Codex candidate\n' >README.md
	: >"$codex_calls"
	CODEX_CALLS_FILE="$codex_calls" HOME="$tmp/home" CODEX_HOME="$tmp/home/.codex" PATH="$no_codex_bin" \
		bash scripts/release.sh 'release: no codex available' >"$tmp/no-codex.out" 2>&1
	[[ ! -s "$codex_calls" ]]
	[[ "$(git ls-remote origin refs/heads/master | awk '{print $1}')" == "$(git rev-parse HEAD)" ]]

	cd "$REPO_ROOT"
	rm -rf -- "$tmp"
}

main() {
	test_manifest_parity
	test_no_agent_plugins_schema_in_root_manifest
	test_sync_migrates_legacy_codex_links
	test_codex_source_exclusions_are_idempotent
	test_development_refresh_restores_manifest
	test_release_refresh_ordering
	printf 'Codex plugin regression tests passed\n'
}

main "$@"
