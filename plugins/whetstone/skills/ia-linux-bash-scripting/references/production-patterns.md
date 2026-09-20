# Production patterns

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

**Atomic file write** -- run the producer into a temp file, then rename only after it succeeds:
```bash
atomic_write() {
    local target=$1 tmp
    shift
    tmp=$(mktemp -- "${target}.tmp.XXXXXXXX") || return
    if "$@" >"$tmp" && mv -fT -- "$tmp" "$target"; then
        return 0
    else
        local rc=$?
        rm -f -- "$tmp"
        return "$rc"
    fi
}
atomic_write /etc/app/config.yml generate_config
```

The producer must return nonzero on generation failure; explicitly propagate failures inside shell functions because Bash suppresses `errexit` in this conditional context. Pipeline producers must enable `pipefail`. Do not pipe into this helper: an upstream failure cannot prevent a rename that already happened.

**Atomic multi-file activation** -- N individually atomic copies are not an atomic interface: a failure after replacing the second of three leaves the old entry point running against a mixed set. Stage the release into a fresh uniquely-named directory, then swap one relative `current` symlink (`ln -sfn` onto a temp name, then `mv -T` it into place). A component that cannot join the swap -- a separately installed helper that an already-running caller invokes -- is installed *first*, so an interrupted run lands on old-caller/new-helper, and the helper's interface stays backward compatible. The failure fixture seeds a complete prior release, fails after one new component is staged, and asserts every prior component is still active.

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
- Distinguish syscall modes from utility options: umask masks a `mkdir(2)` mode, but GNU `mkdir -m 755` explicitly sets the resulting directory to `0755` even under `umask 077`. For a mode-preservation test, set the fixture's mode explicitly and assert the observed result; do not loosen the service's umask.
- Staging a file across users through a world-writable directory fails on the rename, not the read: `/tmp`'s sticky bit lets only the file's owner rename or unlink it, so a second user's `mv /tmp/f "$dest"` fails with `Operation not permitted` while `cp` succeeds. Copy as the destination user (`sudo -u <dest> cp -- /tmp/f "$target"`), then remove the staging copy as its creator
- Moving a secret out of argv into a temp file closes the `ps` / `/proc/<pid>/cmdline` exposure and nothing else. Bash stores a multi-line command as **one** history entry, heredoc body included, and the single-line form `printf %s '<value>' >"$tmp"` puts the value on the command line too. Take it from stdin and let a JSON-aware writer escape it:
  ```bash
  umask 077; tmp=$(mktemp); trap 'rm -f -- "$tmp"' EXIT
  read -rs SECRET                                   # stdin: never a command line, never in history
  printf '%s' "$SECRET" | jq -Rs '{Password:.}' >"$tmp"
  ```
  Bash's builtin `printf` sends the value through stdin, avoiding `jq --arg`'s process-argument exposure; `jq -Rs` escapes JSON characters. Use `mktemp` rather than a predictable path that an attacker can replace with a symlink.
- Generate secret/token files with no trailing newline. `cmd >"$f"` keeps the `\n`, `$(cat "$f")` strips it, and CLI arguments of the `file://$f` shape transmit it verbatim -- so one generated value installed into two consumers differs by one byte while both sides *display* the same characters and every constant-time comparison on the far side just returns false. Fix at the generator (`printf %s "$(cmd)" >"$f"`), never per reader, and verify with `wc -c < "$f"`
- Signal cleanup: use `trap 'cleanup; exit 130' INT` and `trap 'cleanup; exit 143' TERM` to report the conventional signal-specific exit status.
- A script that shells out to a coding-agent or automation CLI with a prompt or task file whose content the script's author does not fully control (a ticket body, a generated plan, a file from another repo) must default to that CLI's most restrictive approval and execution mode. Never hardcode a full-auto or bypass flag. The task content is an indirect prompt-injection surface, so the execution mode is the last boundary the script can still enforce. Where an operator override is supported, validate the value against an explicit allowlist and reject anything unrecognized instead of passing it through:
  ```bash
  mode=${AGENT_MODE:-read-only}
  case $mode in
      read-only|ask) ;;
      *) die "Unsupported AGENT_MODE: $mode" ;;
  esac
  agent_cli --approval-mode "$mode" --task-file "$task"
  ```
  The allowlist deliberately omits the CLI's unattended mode; adding it is a reviewed change to the script, not an environment variable.

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
| A multi-command shell block embedded in YAML or a `RUN` line | Select Bash explicitly before using `set -Eeuo pipefail`; these options are not portable to `sh`. Match the production interpreter and flags in tests. Capture failures before a trailing successful command can hide them, and keep intentional fallbacks explicit. |
