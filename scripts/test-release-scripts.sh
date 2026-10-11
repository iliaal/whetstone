#!/usr/bin/env bash
# Regression tests for the release tooling: release.sh branch preflight,
# mirror-to-ai-skills.sh branch check, generate-manifest.py bundle hashing, and
# publish-clawhub.sh bundle-based change detection. Every case runs against
# throwaway repos under a temp dir with fake gh/npx; nothing is pushed or published.
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/whetstone-release-tests.XXXXXXXX")
trap 'rm -rf -- "$TMP_ROOT"' EXIT
FAILURES=0

fail() {
	printf 'FAIL: %s\n' "$*" >&2
	FAILURES=$((FAILURES + 1))
}

# Reports a case as passing only if it recorded no failures since $1.
pass() {
	local since="$1"
	shift
	((FAILURES == since)) && printf 'ok:   %s\n' "$*"
	return 0
}

git_init_repo() {
	local dir="$1"
	git init -q -b master "$dir"
	git -C "$dir" config user.email test@example.invalid
	git -C "$dir" config user.name Test
	git -C "$dir" config commit.gpgsign false
}

# Creates $1/{origin.git,work,home/ai/ai-skills,ai-origin.git,bin} with both
# repos on master, in sync with their bare origins, and release.sh copied in.
make_release_fixture() {
	local root="$1"
	mkdir -p "$root/bin" "$root/home/ai"
	# shellcheck disable=SC2016  # $0 must expand inside the fake command, not here
	printf '#!/usr/bin/env bash\nprintf "fake %%s called\\n" "$(basename "$0")" >>"%s/calls"\nexit 1\n' "$root" >"$root/bin/gh"
	cp "$root/bin/gh" "$root/bin/npx"
	chmod +x "$root/bin/gh" "$root/bin/npx"

	git init -q --bare "$root/origin.git"
	git_init_repo "$root/work"
	mkdir -p "$root/work/scripts"
	cp "$REPO_ROOT/scripts/release.sh" "$root/work/scripts/release.sh"
	printf 'version=1.0.0\n' >"$root/work/manifest"
	git -C "$root/work" add .
	git -C "$root/work" commit -q -m initial
	git -C "$root/work" remote add origin "$root/origin.git"
	git -C "$root/work" push -q -u origin master

	git init -q --bare "$root/ai-origin.git"
	git_init_repo "$root/home/ai/ai-skills"
	mkdir -p "$root/home/ai/ai-skills/skills"
	printf '# Changelog\n' >"$root/home/ai/ai-skills/CHANGELOG.md"
	git -C "$root/home/ai/ai-skills" add .
	git -C "$root/home/ai/ai-skills" commit -q -m initial
	git -C "$root/home/ai/ai-skills" remote add origin "$root/ai-origin.git"
	git -C "$root/home/ai/ai-skills" push -q -u origin master
}

run_release() {
	local root="$1"
	(cd "$root/work" && HOME="$root/home" PATH="$root/bin:$PATH" bash scripts/release.sh 'release: fixture') >"$root/out" 2>&1
}

# Release must abort before committing, pushing, tagging, or publishing.
assert_release_aborts() {
	local start=$FAILURES
	local root="$1" name="$2" expect="$3" origin_before ai_before head_before
	origin_before=$(git --git-dir="$root/origin.git" rev-parse master)
	ai_before=$(git --git-dir="$root/ai-origin.git" rev-parse master)
	head_before=$(git -C "$root/work" rev-parse HEAD)
	if run_release "$root"; then
		fail "$name: release.sh exited 0"
		return
	fi
	grep -qF -- "$expect" "$root/out" || fail "$name: missing '$expect' in output: $(cat "$root/out")"
	[[ "$(git --git-dir="$root/origin.git" rev-parse master)" == "$origin_before" ]] || fail "$name: origin master moved"
	[[ "$(git --git-dir="$root/ai-origin.git" rev-parse master)" == "$ai_before" ]] || fail "$name: ai-skills origin master moved"
	[[ "$(git -C "$root/work" rev-parse HEAD)" == "$head_before" ]] || fail "$name: release committed"
	[[ ! -s "$root/calls" ]] || fail "$name: gh/npx invoked: $(cat "$root/calls")"
	pass "$start" "$name"
}

test_release_aborts_off_master() {
	local root="$TMP_ROOT/off-master"
	make_release_fixture "$root"
	git -C "$root/work" switch -q -c release-work
	printf 'version=1.1.0\n' >"$root/work/manifest"
	git -C "$root/work" commit -q -am 'bump v1.1.0'
	assert_release_aborts "$root" "release.sh aborts on a non-master branch" "whetstone is on 'release-work', not 'master'"
}

test_release_aborts_detached() {
	local root="$TMP_ROOT/detached"
	make_release_fixture "$root"
	git -C "$root/work" switch -q --detach
	assert_release_aborts "$root" "release.sh aborts on detached HEAD" "whetstone is on 'detached HEAD'"
}

test_release_aborts_behind_origin() {
	local root="$TMP_ROOT/behind" other="$TMP_ROOT/behind-other"
	make_release_fixture "$root"
	git clone -q "$root/origin.git" "$other"
	git -C "$other" -c user.email=t@example.invalid -c user.name=T -c commit.gpgsign=false commit -q --allow-empty -m 'remote-only'
	git -C "$other" push -q origin master
	assert_release_aborts "$root" "release.sh aborts when local master lacks origin/master" "is behind or diverged from origin/master"
}

test_release_aborts_ai_skills_off_master() {
	local root="$TMP_ROOT/ai-branch"
	make_release_fixture "$root"
	git -C "$root/home/ai/ai-skills" switch -q -c stray
	assert_release_aborts "$root" "release.sh aborts when ai-skills is off master" "ai-skills is on 'stray', not 'master'"
}

test_release_aborts_ai_skills_dirty() {
	local root="$TMP_ROOT/ai-dirty"
	make_release_fixture "$root"
	printf 'stray\n' >"$root/home/ai/ai-skills/untracked.txt"
	assert_release_aborts "$root" "release.sh aborts when ai-skills has uncommitted files" "ai-skills working tree is not clean"
}

test_mirror_aborts_off_master() {
	local start=$FAILURES
	local root="$TMP_ROOT/mirror" out
	make_release_fixture "$root"
	git -C "$root/home/ai/ai-skills" switch -q -c stray
	if out=$(HOME="$root/home" bash "$REPO_ROOT/scripts/mirror-to-ai-skills.sh" --dry-run 2>&1); then
		fail "mirror-to-ai-skills.sh exited 0 with ai-skills on 'stray'"
		return
	fi
	[[ "$out" == *"is on 'stray', not 'master'"* ]] || fail "mirror: unexpected output: $out"
	pass "$start" "mirror-to-ai-skills.sh aborts when ai-skills is off master"
}

# Minimal plugin tree that generate-manifest.py and publish-clawhub.sh can run
# against. Scripts are copied in so REPO_ROOT resolves to the fixture.
make_manifest_fixture() {
	local root="$1" version="$2"
	git_init_repo "$root"
	mkdir -p "$root/scripts" "$root/distillery" "$root/plugins/whetstone/.claude-plugin" \
		"$root/plugins/whetstone/hooks" \
		"$root/plugins/whetstone/skills/ia-alpha/references" \
		"$root/plugins/whetstone/skills/ia-beta"
	cp "$REPO_ROOT/scripts/generate-manifest.py" "$REPO_ROOT/scripts/publish-clawhub.sh" "$root/scripts/"
	printf '{"name":"whetstone","version":"%s"}\n' "$version" >"$root/plugins/whetstone/.claude-plugin/plugin.json"
	printf "SKILL_PATTERNS[ia-alpha]='alpha'\nSKILL_PATTERNS[ia-beta]='beta'\n" >"$root/plugins/whetstone/hooks/skill-patterns.sh"
	printf -- '---\nname: ia-alpha\n---\nAlpha\n' >"$root/plugins/whetstone/skills/ia-alpha/SKILL.md"
	printf 'alpha reference v1\n' >"$root/plugins/whetstone/skills/ia-alpha/references/guide.md"
	printf -- '---\nname: ia-beta\n---\nBeta\n' >"$root/plugins/whetstone/skills/ia-beta/SKILL.md"
	printf '__pycache__/\n' >"$root/.gitignore"
	git -C "$root" add .
	git -C "$root" commit -q -m initial
}

set_version() {
	printf '{"name":"whetstone","version":"%s"}\n' "$2" >"$1/plugins/whetstone/.claude-plugin/plugin.json"
}

field() {
	jq -r --arg s "$2" --arg f "$3" '.skills[$s][$f] // "null"' "$1/distillery/.skill-versions.json"
}

test_manifest_and_publish_bundle_detection() {
	local start=$FAILURES
	local root="$TMP_ROOT/manifest" out alpha_bundle
	make_manifest_fixture "$root" "1.0.0"
	python3 "$root/scripts/generate-manifest.py" 2>/dev/null
	alpha_bundle=$(field "$root" ia-alpha bundle_hash)

	# Gitignored bytecode inside the skill dir must not change the bundle hash.
	mkdir -p "$root/plugins/whetstone/skills/ia-alpha/references/__pycache__"
	printf 'junk' >"$root/plugins/whetstone/skills/ia-alpha/references/__pycache__/x.pyc"
	set_version "$root" "1.0.1"
	python3 "$root/scripts/generate-manifest.py" 2>/dev/null
	[[ "$(field "$root" ia-alpha bundle_hash)" == "$alpha_bundle" ]] || fail "ignored file changed bundle_hash"
	[[ "$(field "$root" ia-alpha bundle_changed)" == "1.0.0" ]] || fail "ignored file bumped bundle_changed"
	pass "$start" "generate-manifest ignores gitignored files in a skill dir"

	# References-only edit: bundle bumps, SKILL.md content (eval staleness) does not.
	printf 'alpha reference v2\n' >"$root/plugins/whetstone/skills/ia-alpha/references/guide.md"
	set_version "$root" "1.1.0"
	python3 "$root/scripts/generate-manifest.py" 2>/dev/null
	[[ "$(field "$root" ia-alpha bundle_changed)" == "1.1.0" ]] || fail "references-only edit did not bump bundle_changed"
	[[ "$(field "$root" ia-alpha content_changed)" == "1.0.0" ]] || fail "references-only edit bumped content_changed"
	[[ "$(field "$root" ia-beta bundle_changed)" == "1.0.0" ]] || fail "untouched skill bumped bundle_changed"
	pass "$start" "generate-manifest detects a references-only change in bundle_changed only"

	out=$(PATH="$TMP_ROOT/release-bin:$PATH" bash "$root/scripts/publish-clawhub.sh" --dry-run 2>&1)
	[[ "$out" == *"would publish ia-alpha"* ]] || fail "publish dry-run skipped references-only change: $out"
	[[ "$out" == *"unchanged    ia-beta"* ]] || fail "publish dry-run did not skip unchanged skill: $out"
	pass "$start" "publish-clawhub.sh --dry-run publishes the references-only change and skips the unchanged skill"

	# A new, not-yet-staged reference file is part of what the release commits.
	printf 'new\n' >"$root/plugins/whetstone/skills/ia-beta/notes.md"
	set_version "$root" "1.2.0"
	python3 "$root/scripts/generate-manifest.py" 2>/dev/null
	[[ "$(field "$root" ia-beta bundle_changed)" == "1.2.0" ]] || fail "new untracked file did not bump bundle_changed"
	pass "$start" "generate-manifest counts untracked, non-ignored files"

	# Pre-bundle manifests (no bundle_hash) stamp every skill once at the current version.
	jq '.skills |= with_entries(.value |= del(.bundle_hash, .bundle_changed))' \
		"$root/distillery/.skill-versions.json" >"$root/old.json"
	mv "$root/old.json" "$root/distillery/.skill-versions.json"
	set_version "$root" "1.3.0"
	python3 "$root/scripts/generate-manifest.py" 2>/dev/null
	[[ "$(field "$root" ia-alpha bundle_changed)" == "1.3.0" && "$(field "$root" ia-beta bundle_changed)" == "1.3.0" ]] \
		|| fail "pre-bundle manifest did not stamp every skill"
	[[ "$(field "$root" ia-alpha content_changed)" == "1.0.0" ]] || fail "migration bumped content_changed"
	pass "$start" "generate-manifest migrates a pre-bundle manifest by republishing every skill once"
}

test_release_aborts_off_master
test_release_aborts_detached
test_release_aborts_behind_origin
test_release_aborts_ai_skills_off_master
test_release_aborts_ai_skills_dirty
test_mirror_aborts_off_master
mkdir -p "$TMP_ROOT/release-bin"
printf '#!/usr/bin/env bash\nprintf "npx must not run in dry-run\\n" >&2\nexit 99\n' >"$TMP_ROOT/release-bin/npx"
chmod +x "$TMP_ROOT/release-bin/npx"
test_manifest_and_publish_bundle_detection

if ((FAILURES > 0)); then
	printf '%d release-script test(s) failed\n' "$FAILURES" >&2
	exit 1
fi
printf 'Release script tests passed\n'
