---
name: ia-linux-bash-scripting
class: language
description: >-
  Defensive Bash scripting for Linux: safe foundations, argument parsing,
  production patterns, ShellCheck compliance. Use when writing bash scripts,
  shell scripts, cron jobs, or CLI tools in bash.
paths: "**/*.sh,**/*.bash"
---

# Linux Bash Scripting

Produce bash scripts that pass `shellcheck --enable=all` and `shfmt -d` with zero warnings.

Target: GNU Bash 4.4+ on Linux. No macOS/BSD workarounds, no Windows paths, no POSIX-only restrictions.

## Script Foundation

```bash
#!/usr/bin/env bash
set -Eeuo pipefail
shopt -s inherit_errexit

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

trap 'printf "Error at %s:%d\n" "${BASH_SOURCE[0]}" "$LINENO" >&2' ERR
trap 'rm -rf -- "${_tmpdir:-}"' EXIT
```

- `-E` propagates ERR traps into functions
- `inherit_errexit` propagates errexit into `$()`  command substitutions
- Resolve the script's own data files against `SCRIPT_DIR`, never the caller's cwd or `git rev-parse --show-toplevel`. A shared linter invoked from another project's git hook, a cron job, or a wrapper runs with someone else's cwd, so a caller-relative rules path resolves to a file that does not exist: the rule set loads empty, zero violations are found, exit 0. It is a silent no-op, not an error, and running it from inside its own repo passes for the wrong reason. Exercise it once from a scratch directory that is not the script's own tree
- Always create temp dirs under the EXIT trap: `_tmpdir=$(mktemp -d)`
- Wrap body in `main() { ... }` with source guard: `[[ "${BASH_SOURCE[0]}" == "$0" ]] && main "$@"` -- enables sourcing for testing

## Core Rules

- Quote every expansion: `"$var"`, `"$(cmd)"`, `"${array[@]}"`
- `local` for function variables, `local -r` for function constants, `readonly` for script constants
- `printf '%s\n'` over `echo` -- predictable behavior, no flag interpretation
- `[[ ]]` for conditionals; `(( ))` for arithmetic; `$()` over backticks
- End options with `--`: `rm -rf -- "$path"`, `grep -- "$pattern" "$file"`
- Require env vars: `: "${VAR:?must be set}"`
- Never `eval` user input; build commands as arrays: `cmd=("grep" "--" "$pat" "$f"); "${cmd[@]}"`
- Keep untrusted/derived bytes off the command line: never build a heredoc body or an `sh -c` string from external data. An unquoted `<<EOF` command-substitutes `$(...)`/backticks in the content, and even a quoted `<<'EOF'` breaks if a content line equals the delimiter (the heredoc ends early and the rest runs as shell). Write the data to a file with a non-shell writer and have the consumer read the file
- Allowlisting a command? Match the whole command against an anchored pattern (`^…$`), never inspect individual arguments — shell operators (`;`, `&&`, `|`, `#`, newline) smuggle a second command past a per-argument check (`rm -rf node_modules; rm -rf /`). Unrecognized syntax must fail closed to deny/ask
- Validating a path component before it reaches a destructive command? Anchor it against an allowlist (`[[ "$name" =~ ^[a-z0-9][a-z0-9._-]*$ ]]`) before `rm -rf -- "$base/$name"` -- a prefix/`startswith` check on the joined path is defeated by `../` (`$base/../x` still starts with `$base`) and by a sibling directory sharing the prefix (`/srv/app` matches `/srv/app2`). When a full path must be accepted, `realpath -e` it and compare against the resolved base plus a trailing slash
- Validate a numeric before it reaches `(( ))` or `$(( ))` when it came from a file, env var, or command output rather than a literal. Two distinct failures: **(1) command execution** -- arithmetic evaluates an array subscript, so a value of `a[$(cmd)]` runs `cmd` (a bare `$(cmd)` is only a syntax error, so testing that form will wrongly suggest the trap isn't real); **(2) octal abort** -- a leading zero makes `08` base-8 and `$(( v + 1 ))` dies with `value too great for base`, taking the script down under `set -e`. Gate on `[[ "$v" =~ ^-?[0-9]+$ ]]` first, then force base 10 with `$(( 10#$v ))` for zero-padded input
- Separate `local` from assignment to preserve exit codes: `local val; val=$(cmd)`
- Debug tracing: `PS4='+${BASH_SOURCE[0]}:${LINENO}: '` with `bash -x` -- shows file:line per command
- Named exit codes: `readonly EX_USAGE=64 EX_CONFIG=78` -- no magic numbers in `exit`
- Pipeline diagnostics: `"${PIPESTATUS[@]}"` shows exit code of each pipe stage, not just last failure
- Branch on a probe's exact exit status, not on nonzero-versus-zero. A tool that exits 2 for "ran, found nothing" and 128 for "could not run" collapses into a single negative under `if ! cmd`, and stderr is often empty for both. Treating every silent nonzero as "absent" converts a network, permission, or spawn failure into a confident false diagnosis
- `A || B` is a fallback only when `A` **fails** on the case `B` exists for. When `A` succeeds while doing the wrong thing -- resolving a different tool, default, or directory -- `B` is dead code and the wrong behavior is silent. Same trap in `${VAR:-default}` on a path two processes must agree on: whoever lacks `VAR` gets a different location, the two silently stop sharing state, and neither errors. Pick one resolution and fail loudly when it is unavailable

## Safe Iteration

```bash
# NUL-delimited file processing
while IFS= read -r -d '' f; do
    process "$f"
done < <(find /path -type f -name '*.log' -print0)

# Array from command output
readarray -t lines < <(command)
readarray -d '' files < <(find . -print0)

# Glob with no-match guard
for f in *.txt; do [[ -e "$f" ]] || continue; process "$f"; done
```

## Argument Parsing

```bash
verbose=false; output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        -v|--verbose) verbose=true; shift ;;
        -o|--output)  output="$2"; shift 2 ;;
        -h|--help)    usage; exit 0 ;;
        --)           shift; break ;;
        -*)           printf 'Unknown: %s\n' "$1" >&2; exit 1 ;;
        *)            break ;;
    esac
done
```

A single-destination override flag (`--out FILE`) combined with more than one positional target clobbers silently -- last write wins, no error, no diagnostic. Detect the combination (`(( ${#targets[@]} > 1 )) && [[ -n "$output" ]]`) and exit `EX_USAGE` instead of letting the last target overwrite every prior one.

## Production Patterns

**Dependency check:**
```bash
require() { command -v "$1" &>/dev/null || { printf 'Missing: %s\n' "$1" >&2; exit 1; }; }
require jq; require curl
```

**Dry-run wrapper:**
```bash
run() { if [[ "${DRY_RUN:-}" == "1" ]]; then printf '[dry] %s\n' "$*" >&2; else "$@"; fi; }
run cp "$src" "$dst"
```

**Atomic file write** -- write to temp, rename into place:
```bash
atomic_write() { local tmp; tmp=$(mktemp); cat >"$tmp"; mv -- "$tmp" "$1"; }
generate_config | atomic_write /etc/app/config.yml
```

**Retry with backoff:**
```bash
retry() { local n=0 max=5 delay=1; until "$@"; do ((++n>=max)) && return 1; sleep $delay; ((delay*=2)); done; }
retry curl -fsSL "$url"
```

**Script locking** -- prevent concurrent runs:
```bash
exec 9>/var/lock/"${0##*/}".lock
flock -n 9 || { printf 'Already running\n' >&2; exit 1; }
```

**Idempotent operations** -- safe to rerun:
```bash
ensure_dir()  { [[ -d "$1" ]] || mkdir -p -- "$1"; }
ensure_link() { [[ -L "$2" ]] || ln -s -- "$1" "$2"; }
```

A linear script with irreversible steps (commit, push, tag, publish) must be re-runnable from any failure point, not just idempotent per primitive: make each step check-and-skip (`release_exists "$tag" || create_release "$tag"`) so a failure at step 4 is repaired by one re-invocation instead of a hand-reconstruction of steps 4-6.

**Input validation:** `[[ "$1" =~ ^[1-9][0-9]*$ ]] || die "Invalid: $1"` -- validate at script boundaries with `[[ =~ ]]`. The leading `[1-9]` also excludes zero-padded input, which arithmetic would read as octal; widening this to `^[0-9]+$` to admit `0` reintroduces that trap unless the value goes through `10#`

- `umask 077` for scripts creating sensitive files
- Moving a secret out of argv into a temp file closes the `ps` / `/proc/<pid>/cmdline` exposure and nothing else. Bash stores a multi-line command as **one** history entry, heredoc body included, and the single-line form `printf %s '<value>' >"$tmp"` puts the value on the command line too. Take it from stdin and let a JSON-aware writer escape it:
  ```bash
  umask 077; tmp=$(mktemp); trap 'rm -f -- "$tmp"' EXIT
  read -rs SECRET                                   # stdin: never a command line, never in history
  jq -n --arg pw "$SECRET" '{Password:$pw}' >"$tmp"
  ```
  `jq --arg` keeps `"` and `\` intact where a heredoc cannot; `mktemp` over a fixed path because `umask` sets the mode of files it *creates* and a predictable name on a shared host is writable through a pre-planted symlink
- Generate secret/token files with no trailing newline. `cmd >"$f"` keeps the `\n`, `$(cat "$f")` strips it, and CLI arguments of the `file://$f` shape transmit it verbatim -- so one generated value installed into two consumers differs by one byte while both sides *display* the same characters and every constant-time comparison on the far side just returns false. Fix at the generator (`printf %s "$(cmd)" >"$f"`), never per reader, and verify with `wc -c < "$f"`
- Signal cleanup: `trap 'cleanup; exit 130' INT TERM` -- preserves correct exit codes for callers

## Logging

```bash
log() { printf '[%s] [%s] %s\n' "$(date -Iseconds)" "$1" "${*:2}" >&2; }
info()  { log INFO "$@"; }
warn()  { log WARN "$@"; }
error() { log ERROR "$@"; }
die()   { error "$@"; exit 1; }
```

## Anti-Patterns

| Bad | Fix |
|-----|-----|
| `for f in $(ls)` | `for f in *; do` or `find -print0 \| while read` |
| `local x=$(cmd)` | `local x; x=$(cmd)` -- preserves exit code |
| `x=$(cmd)` then an `[[ -z $x ]]` fallback check | `x=$(cmd) \|\| true` -- under `set -e` a failed `$()` in a bare assignment aborts the script there, so the fallback never runs (opposite of the `local` case: `local` masks the failure, a bare assignment propagates it) |
| `x=$(cmd 2>/dev/null \|\| echo MISSING)` | Capture and test separately -- a tool that prints to stdout *and* exits nonzero (some echo their unresolved argument before failing) contributes both strings, so `x` becomes `<junk>` + `MISSING` and every comparison built on it reports a spurious difference. The `2>/dev/null` that quiets the loop is also what hides the error line |
| `echo "$data"` | `printf '%s\n' "$data"` |
| `cat file \| grep` | `grep pat file` |
| `kill -9 $pid` first | `kill "$pid"` first, `-9` as last resort |
| `cd dir; cmd` | `cd dir || exit 1` or subshell `(cd dir && cmd)` |

## Performance

- Parameter expansion over externals: `${path%/*}` not `dirname`, `${path##*/}` not `basename`, `${var//old/new}` not `sed`
- `(( ))` over `expr`; `[[ =~ ]]` over `echo | grep`
- Cache results: `val=$(cmd)` once, reuse `$val`
- `xargs -0 -P "$(nproc)"` for parallel work
- `declare -A map` for lookups instead of repeated grep

## Bash 4.4+ / 5.x

- `${var@Q}` shell-quoted, `${var@U}` uppercase, `${var@L}` lowercase
- `declare -n ref=varname` nameref for indirect access
- `wait -n` wait for any background job
- `$EPOCHSECONDS`, `$EPOCHREALTIME` -- timestamps without forking `date`

## Linux-Specific

- GNU coreutils differ from macOS: `sed -i` (no `''` suffix), `grep -P` (PCRE support), `readlink -f` (canonical path)
- `timeout 30s cmd` to prevent automation hangs

## ShellCheck

Run `shellcheck --enable=all script.sh`. Key rules:
- **SC2155**: Separate declaration from assignment
- **SC2086**: Double-quote variables
- **SC2046**: Quote command substitutions
- **SC2164**: `cd dir || exit`
- **SC2327/SC2328**: Use `${BASH_REMATCH[n]}` not `$n` for regex captures

Pre-commit: `shellcheck *.sh && shfmt -i 2 -ci -d *.sh`

## Verify

Run `shellcheck --enable=all` and `shfmt -d` with zero warnings before declaring done. Test edge cases: empty input, missing files, spaces in paths.
