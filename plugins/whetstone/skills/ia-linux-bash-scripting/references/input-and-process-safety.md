# Input and process safety

## Core Rules

- Quote every expansion: `"$var"`, `"$(cmd)"`, `"${array[@]}"`
- `local` for function variables, `local -r` for function constants, `readonly` for script constants
- `printf '%s\n'` over `echo`: predictable behavior, no flag interpretation
- `[[ ]]` for conditionals; `(( ))` for arithmetic; `$()` over backticks
- End options with `--`: `rm -rf -- "$path"`, `grep -- "$pattern" "$file"`
- Require env vars: `: "${VAR:?must be set}"`
- Never `eval` user input; build commands as arrays: `cmd=("grep" "--" "$pat" "$f"); "${cmd[@]}"`
- Keep untrusted/derived bytes off the command line: never build a heredoc body or an `sh -c` string from external data. An unquoted `<<EOF` command-substitutes `$(...)`/backticks in the content, and even a quoted `<<'EOF'` breaks if a content line equals the delimiter (the heredoc ends early and the rest runs as shell). Write the data to a file with a non-shell writer and have the consumer read the file
- Allowlisting a command? Match the whole command against an anchored pattern (`^…$`), never inspect individual arguments; shell operators (`;`, `&&`, `|`, `#`, newline) smuggle a second command past a per-argument check (`rm -rf node_modules; rm -rf /`). Unrecognized syntax must fail closed to deny/ask
- Validating a path component before it reaches a destructive command? Anchor it against an allowlist (`[[ "$name" =~ ^[a-z0-9][a-z0-9._-]*$ ]]`) before `rm -rf -- "$base/$name"`. A prefix/`startswith` check on the joined path is defeated by `../` (`$base/../x` still starts with `$base`) and by a sibling directory sharing the prefix (`/srv/app` matches `/srv/app2`). When a full path must be accepted, `realpath -e` it and compare against the resolved base plus a trailing slash
- Validate external numeric text before arithmetic: array subscripts can execute commands, and leading zeros select octal. Require `[[ "$v" =~ ^-?[0-9]+$ ]]`, separate an optional minus from the digits, reject magnitudes outside the application's range before arithmetic conversion, convert the unsigned digits with `10#`, then apply the sign. `10#-08` is invalid. See Bounded signed decimal conversion below.
- Separate `local` from assignment to preserve exit codes: `local val; val=$(cmd)`
- Debug tracing: `PS4='+${BASH_SOURCE[0]}:${LINENO}: '` with `bash -x` shows file:line per command
- Named exit codes: `readonly EX_USAGE=64 EX_CONFIG=78`; no magic numbers in `exit`
- Pipeline diagnostics: `"${PIPESTATUS[@]}"` shows exit code of each pipe stage, not just last failure
- Branch on a probe's exact exit status, not on nonzero-versus-zero. A tool that exits 2 for "ran, found nothing" and 128 for "could not run" collapses into a single negative under `if ! cmd`, and stderr is often empty for both. Treating every silent nonzero as "absent" converts a network, permission, or spawn failure into a confident false diagnosis
- `A || B` is a fallback only when `A` **fails** on the case `B` exists for. When `A` succeeds while doing the wrong thing (resolving a different tool, default, or directory), `B` is dead code and the wrong behavior is silent. Same trap in `${VAR:-default}` on a path two processes must agree on: whoever lacks `VAR` gets a different location, the two silently stop sharing state, and neither errors. Pick one resolution and fail loudly when it is unavailable. A fallback chain must also test *usability*, not presence: `${XDG_RUNTIME_DIR:-/tmp}` falls through only when the variable is unset, so a variable pointing at an unwritable directory takes `mkdir` to `EACCES` and aborts on the step the chain made optional. Treat a permission or existence failure on a configured location the same as an unconfigured one, and log which candidate was chosen
- A `;` list exits with its *last* command's status, so appending a status echo guarantees success: `./run.sh > log 2>&1; echo "EXIT=$?"` exits 0 no matter what `run.sh` did. Capture and re-raise: `rc=$?; printf 'EXIT=%d\n' "$rc"; exit "$rc"`. A redirection binds only to its own command, so in `job >log 2>&1; echo DONE` the sentinel goes to stdout, not `log`, and a watcher running `until grep -q DONE log` spins forever; wait on the process (`wait "$pid"`) instead of a sentinel
- Under `pipefail`, an early `grep -q` exit can make a matching pipeline fail when its producer takes SIGPIPE. For expected nonzero commands, guard capture against `errexit`, save the exact status, then assert status and output: `if out=$(cmd 2>&1); then status=0; else status=$?; fi; [[ $status -eq 2 ]]; grep -q -- "$pattern" <<<"$out"`. Use the command's actual expected status. For Bash functions whose internal `errexit` behavior matters, run a separate executable with explicit error propagation; a conditional call can suppress their internal `errexit` checks.
- Never `pkill -f` or `killall` a tool name. `pkill -f node` signals every process on the host whose argv contains the pattern, including other users' and sessions' runs. Record `$!` at launch and `kill "$pid"`; when a search is unavoidable, match a token only the target carries, then still kill the one PID
- A wait loop that greps for the process it waits on matches itself: `pgrep -f` tests the full argv and the pattern sits in the waiter's own command line, so `until ! pgrep -f build_step; do sleep 10; done` never exits. A pipeline feeding `ps` straight into a matcher includes the matcher's own process the same way, and an empty substitution collapses `/proc/$(pgrep -f cmd | head -1)` to `/proc/`, which always exists. Match the exact process name (`pgrep -x`), drop your own PID (`pgrep -f "$pat" | grep -vx "$$"`), take the snapshot in one command and filter the saved output in the next, and prefer waiting on the process directly (`wait`, `flock`) over polling for it. A `[p]attern` bracket in a target's own argv also hides it from `ps | grep pattern`, so an empty search is evidence about the query before it is evidence about the process table


## Safe Iteration

```bash
scan_root=${1:?directory required}
readonly EX_USAGE=64
[[ $scan_root == /* ]] || scan_root="./$scan_root"
if [[ ! -d $scan_root ]]; then
    printf 'Not a directory: %s\n' "$scan_root" >&2
    exit "$EX_USAGE"
fi
files_file=$(mktemp)
trap 'rm -f -- "$files_file"' EXIT
if find "$scan_root" -type f -name '*.log' -print0 >"$files_file"; then
    :
else
    status=$?
    exit "$status"
fi
while IFS= read -r -d '' f; do
    printf '%s\0' "$f"
done <"$files_file"
```

Process substitution (`< <(producer)`) does not transfer the producer's exit status to `while` or `readarray`, even under `pipefail`. Consume only after the producer succeeds. For an array, use `readarray -d '' files <"$files_file"` instead of the loop; for line data, check its producer first, then use `readarray -t lines <"$text_file"`. Integrate temporary-file cleanup with an existing EXIT trap rather than replacing it.

For glob iteration, guard the no-match case:

```bash
for f in *.txt; do [[ -e "$f" ]] || continue; process "$f"; done
```

## Argument Parsing

```bash
readonly EX_USAGE=64
usage() { printf 'Usage: %s [-v] [-o FILE|--output=FILE] [--] TARGET...\n' "${0##*/}"; }
verbose=false; output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        -v|--verbose) verbose=true; shift ;;
        -o|--output)
            if [[ $# -lt 2 || -z $2 || $2 == -* ]]; then
                printf 'Missing value for %s\n' "$1" >&2
                usage >&2
                exit "$EX_USAGE"
            fi
            output="$2"; shift 2 ;;
        --output=*)
            output=${1#*=}
            if [[ -z $output ]]; then usage >&2; exit "$EX_USAGE"; fi
            shift ;;
        -h|--help)    usage; exit 0 ;;
        --)           shift; break ;;
        -*)           printf 'Unknown: %s\n' "$1" >&2; usage >&2; exit "$EX_USAGE" ;;
        *)            break ;;
    esac
done
```

A single-destination override flag (`--out FILE`) combined with more than one positional target clobbers silently: last write wins, no error, no diagnostic. Detect the combination (`(( ${#targets[@]} > 1 )) && [[ -n "$output" ]]`) and exit `EX_USAGE` instead of letting the last target overwrite every prior one.


## Bounded signed decimal conversion

Accept integers from -999999999 to 999999999 in this example, including zero padding. Choose and check the application's actual range before arithmetic; Bash integers do not detect overflow.

```bash
parse_decimal() {
    local raw=${1-} digits sign=1
    [[ "$raw" =~ ^-?[0-9]+$ ]] || return 64
    digits=${raw#-}
    [[ "$raw" != -* ]] || sign=-1
    while [[ ${#digits} -gt 1 && "$digits" == 0* ]]; do
        digits=${digits#0}
    done
    [[ ${#digits} -le 9 ]] || return 64
    printf '%d\n' "$((sign * 10#$digits))"
}
```

Check `08 → 8`, `-08 → -8`, `-0 → 0`, and reject empty text, expression syntax, and magnitudes beyond the bound.
