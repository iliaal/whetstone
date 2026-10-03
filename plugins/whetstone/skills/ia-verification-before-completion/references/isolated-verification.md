# Isolated Verification

A green build or test run in the working tree is not proof the change is sound. Unrelated work-in-progress already present (uncommitted edits, untracked files, a sibling branch's leftovers) can supply a missing symbol, satisfy an import, or mask a break that the change alone would expose. The contaminated local pass is not the evidence; a clean pass in isolation is.

When the change is high-stakes (touches shared modules consumed elsewhere) or the tree cannot be made clean first, reproduce the pass against an explicit known-good base with only the selected owned delta applied.

1. Resolve the base and enumerate exact repository-relative file paths, including deleted paths, both sides of renames, and selected untracked files. Do not use directory or glob selections.
2. Choose the snapshot source. Leave `owned_patch` empty only when every base-to-current difference in each selected file is owned; this mode captures current bytes, including committed, staged, unstaged, and selected untracked work. It does not verify a staged-only or PR-head scope.
3. For mixed owned/caller hunks or another selected revision, prepare an owned-only checkout at the base, apply the inspected owned hunks there, and copy only the selected new-file bytes. Stage the explicit files in that scratch checkout and export its reviewed binary `git diff --cached --no-textconv --no-ext-diff --binary <base> -- <paths>` to a private patch file. Set `owned_patch` to that absolute path. Inspect the patch against the requested scope before using it; a whole-file diff from the dirty caller is not an owned patch.
4. Materialize the snapshot using a separate index and a detached worktree. Check the expected tree and actual file content before running verification. Neither snapshot mode writes the caller's files or index.

This recipe requires Git, Bash, and Python 3. Fill the base, exact paths, optional reviewed patch, and build/test commands before running:

```bash
set -euo pipefail
umask 077
export GIT_LITERAL_PATHSPECS=1
repo_root=$(git rev-parse --show-toplevel)
verify_base=$(git -C "$repo_root" rev-parse --verify "<known-good-commit>^{commit}")
owned_paths=(path/to/owned-file path/to/other-owned-file path/to/selected-new-file)
owned_patch=""
scratch_root=$(mktemp -d)
verify_dir="$scratch_root/tree"
snapshot_index="$scratch_root/index"

cleanup() {
    git -C "$repo_root" worktree remove --force "$verify_dir" >/dev/null 2>&1 || true
    rm -rf -- "$scratch_root"
}
trap cleanup EXIT
snapshot_git() {
    GIT_INDEX_FILE="$snapshot_index" git -C "$repo_root" "$@"
}

snapshot_git read-tree "$verify_base"
if [[ -n "$owned_patch" ]]; then
    snapshot_git apply --cached "$owned_patch"
else
    snapshot_git add --all --force -- "${owned_paths[@]}"
fi
expected_tree=$(snapshot_git write-tree)
snapshot_git diff --cached --no-textconv --no-ext-diff --binary "$verify_base" -- "${owned_paths[@]}" > "$scratch_root/owned.patch"

git -C "$repo_root" worktree add --detach "$verify_dir" "$verify_base"
if [[ -s "$scratch_root/owned.patch" ]]; then
    git -C "$verify_dir" apply --index "$scratch_root/owned.patch"
fi
test "$(git -C "$verify_dir" write-tree)" = "$expected_tree"
git -C "$verify_dir" diff --quiet --no-textconv --no-ext-diff

python3 - "$repo_root" "$verify_dir" "$expected_tree" "$owned_patch" "${owned_paths[@]}" <<'PY'
import os
import pathlib
import stat
import subprocess
import sys

repo, target, tree, patch, *paths = sys.argv[1:]

def actual(root, relative):
    path = pathlib.Path(root, relative)
    if path.is_symlink():
        return ("120000", os.fsencode(os.readlink(path)))
    if not path.exists():
        return None
    if not path.is_file():
        raise SystemExit(f"Expected a file path, not a directory: {relative}")
    mode = "100755" if path.stat().st_mode & stat.S_IXUSR else "100644"
    return (mode, path.read_bytes())

for relative in paths:
    parsed = pathlib.PurePosixPath(relative)
    if parsed.is_absolute() or ".." in parsed.parts or relative in ("", "."):
        raise SystemExit(f"Invalid repository-relative file path: {relative}")
    entry = subprocess.check_output(["git", "-C", repo, "ls-tree", "-z", tree, "--", relative])
    if entry:
        metadata, recorded_path = entry.rstrip(b"\0").split(b"\t", 1)
        mode, kind, oid = metadata.split()
        if kind != b"blob" or recorded_path != os.fsencode(relative):
            raise SystemExit(f"Expected one exact blob path: {relative}")
        content = subprocess.check_output(["git", "-C", repo, "cat-file", "blob", oid.decode()])
        expected = (mode.decode(), content)
    else:
        expected = None
    if actual(target, relative) != expected:
        raise SystemExit(f"Materialized content/type/mode mismatch: {relative}")
    if not patch and actual(repo, relative) != expected:
        raise SystemExit(f"Caller bytes changed or Git conversion altered the snapshot: {relative}")
print(f"Verified actual content, type, and executable mode for {len(paths)} selected paths.")
PY

( cd "$verify_dir" && <build-command> && <test-command> )
```

The tree comparison rejects a reviewed patch that changed files outside the selected manifest. The content check rejects missing files, wrong symlink targets, executable-mode drift, and checkout/filter conversions; resolve a mismatch rather than treating an index match as byte-level proof. If another writer changes the selected source during capture, stop and recapture a stable snapshot.

Before running the build or tests, resolve disposable targets under the [Pre-Verification Check](./proof-integrity.md#pre-verification-check). Cleanup removes only the invocation-owned scratch checkout and artifacts. Never stash, reset, stage, or overwrite the caller's files or index for this proof.

A clean pass of the materialized owned change is the proof. A failure there, while the local tree stays green, requires investigation: surrounding WIP may have masked the break, or the isolated environment may differ. State the base SHA, selected paths, snapshot tree, patch/source mode, and actual checks in the verification evidence.
