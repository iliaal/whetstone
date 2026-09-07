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

## Core rules

- Quote expansions, use arrays for commands, and never evaluate external data as shell code.
- Validate numeric syntax, sign, and application bounds before arithmetic. Convert unsigned digits with `10#` before applying the sign; `10#-08` is invalid.
- Keep secrets out of process arguments and tracing. Feed them through stdin and use a JSON-aware encoder.
- Check exact exit statuses where “absent” differs from “failed to inspect.” Separate `local` declarations from command substitutions.
- Use NUL-delimited file iteration, validate required flag values, and reject conflicting output/target combinations.
- For atomic replacement, stage beside the destination; for multi-file activation, switch a single staged release reference.
- Preserve unrelated files and report the actual signal or command status after cleanup.
- Do not assume Bash options work in `sh`, GNU utility modes behave like syscall modes, or a configured fallback path is usable.

## Task-specific references

Read the relevant reference before implementing the matching behavior:

- For command execution, external input, numeric conversion, argument parsing, iteration, or subprocess status handling: [input-and-process-safety.md](./references/input-and-process-safety.md).
- For file activation, secrets, locking, retries, cleanup, permissions, logging, or restartable automation: [production-patterns.md](./references/production-patterns.md).

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
