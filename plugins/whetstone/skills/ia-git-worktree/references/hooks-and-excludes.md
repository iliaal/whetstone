# Hooks and Local Excludes

## Hook Safety Under Husky

Installing hooks into `.git/hooks/` silently fails on any repo that uses Husky. Husky sets `core.hooksPath` (typically to `.husky/_`) and git ignores `.git/hooks/` entirely when that config is non-empty. The hook file lands on disk, is executable, is correct, and is dead. Invisible failure until someone asks why the post-merge behavior isn't running.

### Detection rule before writing any hook

```bash
hooks_path=$(git -C "$repo" config --get core.hooksPath)
```

- Empty output: write to `$(git rev-parse --git-common-dir)/hooks/<name>` as usual.
- `.husky/_` (or any path containing `husky.sh` / `h` trampoline): Husky v9 setup. Write to `.husky/<name>`; do NOT include the v8-era `. "$(dirname "$0")/_/husky.sh"` line (v9 prints a deprecation warning if you do).
- Unrecognized non-empty value: refuse to write the hook and surface the path to the user. Silent writes to the wrong location waste debug cycles later.

### Worktree-safe hook body

`.git/hooks/` lives in the common git dir and runs for every worktree of the clone. A hook installed once fires across all trees. Two rules to stay safe:

1. Resolve the invoking worktree's root inside the hook body with `git rev-parse --show-toplevel`, not a hardcoded path. Hardcoding means the last `install-hooks` invocation wins for every worktree.
2. Guard the tool invocation with an existence check on the tool's per-tree state dir. Siblings without your tool's setup must no-op, not spawn a failing background process per git op.

```sh
#!/bin/sh
root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -d "$root/.my-tool" ] || exit 0
( cd "$root" && my-tool index ) >>"$root/.my-tool/hook.log" 2>&1 &
exit 0
```

Redirect to a log file inside the tool's state dir, not `/dev/null` — silent failures produce stale state you only notice hours later.

## Local Excludes: .git/info/exclude vs .gitignore

Tooling artifacts (local index dirs, hook helpers, per-developer scratch files) belong in `.git/info/exclude`, NOT in the tracked `.gitignore`.

- `.gitignore` is content — tracked, shared with the team, reviewed in PRs. Adding a personal tooling rule there pollutes a shared file. On foreign repos (upstream projects, third-party clones) the rule either rides into a PR by accident or sits as a dirty working tree forever.
- `.git/info/exclude` is local — untracked, lives in the common git dir, shared across every worktree of the clone. Same syntax and semantics as `.gitignore` without the leakage.

### Resolving the path correctly under worktrees

Don't hardcode `$repo/.git/info/exclude`. In a worktree, `.git` is a file (gitlink), not a directory. Use git itself:

```bash
exclude=$(git -C "$repo" rev-parse --git-path info/exclude)
```

### Idempotent append

```bash
line="/.my-tool/"
mkdir -p "$(dirname "$exclude")"
grep -qxF "$line" "$exclude" 2>/dev/null || printf '\n# my-tool\n%s\n' "$line" >> "$exclude"
```

`grep -qxF` matches the exact line with no regex surprises.

### When to break the rule

Only when the artifact is genuinely team-shared and belongs in the repo (build outputs used in CI, generated files, vendored dependencies). If in doubt, ask: "would another contributor benefit from this rule?" If no, exclude locally.
