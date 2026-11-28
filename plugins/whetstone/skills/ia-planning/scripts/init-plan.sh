#!/usr/bin/env bash
# init-plan.sh: scaffold a durable task plan
# Usage: bash init-plan.sh [task-name] [--force]
#
# Creates .plan/task_plan.md at the repository root of the working
# directory (the working directory itself outside a repository)
# Adds .plan/ to that root's .gitignore if not present
# Refuses to overwrite a task_plan.md that still has unchecked tasks
# unless --force is given.

set -euo pipefail

ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)
SKILL_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
# Check the working directory too: a skill installed inside a git checkout
# resolves ROOT to that checkout's root, which lies outside SKILL_ROOT.
for dir in "$(pwd -P)/" "$ROOT/"; do
    case "$dir" in
        "$SKILL_ROOT"/*)
            echo "ERROR: run from the project working tree, not the skill directory ($SKILL_ROOT)." >&2
            exit 2
            ;;
    esac
done
PLAN_DIR="$ROOT/.plan"
GITIGNORE="$ROOT/.gitignore"
FORCE=0
TASK_NAME="Unnamed Task"
for arg in "$@"; do
    case "$arg" in
        --force) FORCE=1 ;;
        *) TASK_NAME="$arg" ;;
    esac
done
DATE=$(date +%Y-%m-%d)

command -v flock >/dev/null 2>&1 || {
    echo "ERROR: flock is required to initialize a plan safely." >&2
    exit 1
}
mkdir -p "${PLAN_DIR}"
exec {plan_lock}>>"${PLAN_DIR}/.init.lock"
flock -x "${plan_lock}"

PLAN_FILE="${PLAN_DIR}/task_plan.md"
if [[ -L "${PLAN_FILE}" || (-e "${PLAN_FILE}" && ! -f "${PLAN_FILE}") ]]; then
    echo "ERROR: ${PLAN_FILE} is not a regular file." >&2
    exit 1
fi

# Guard: an existing plan with unchecked tasks is live work in progress.
if [[ "${FORCE}" -ne 1 && -f "${PLAN_FILE}" ]]; then
    if grep -q '^[[:space:]]*- \[ \]' "${PLAN_FILE}"; then
        echo "ERROR: ${PLAN_FILE} has unchecked tasks." >&2
        echo "Same work continuing: update it in place. Different work: confirm which plan wins, then re-run with --force." >&2
        exit 1
    elif [[ $? -ne 1 ]]; then
        exit 1
    fi
fi

if ! grep -qxF '.plan/' "$GITIGNORE" 2>/dev/null; then
    if [[ -s "$GITIGNORE" ]]; then
        ignore_last_byte=$(tail -c 1 "$GITIGNORE")
        if [[ -n "${ignore_last_byte}" ]]; then
            printf '\n' >>"$GITIGNORE"
        fi
    fi
    printf '%s\n' '.plan/' >>"$GITIGNORE"
fi

TEMP_PLAN=$(mktemp "${PLAN_DIR}/.task_plan.XXXXXXXXXX")
trap 'rm -f -- "${TEMP_PLAN}"' EXIT
cat >"${TEMP_PLAN}" <<EOF
# Plan: ${TASK_NAME}

**Created:** ${DATE}

## Approach

[1-3 sentences: what and why]

## Scope

- **In**: [what's included]
- **Out**: [what's explicitly excluded]

## Next Step

[one line: the phase and task to resume on]

## Phase 1: [Name]

**Status**: pending
**Files**: [specific files owned by this phase]

**Tasks**:
- [ ] [Verb-first atomic task]

**Verify**: [specific test command or assertion]
**Exit**: [clear done definition]

## Open Questions

- [Only genuinely blocking unknowns]

## Error Log

| Attempt | What Failed | Why | Next Action |
|---------|-------------|-----|-------------|
EOF
mv -fT -- "${TEMP_PLAN}" "${PLAN_FILE}"

echo "Created ${PLAN_DIR}/ with:"
echo "  - task_plan.md"
echo "Added .plan/ to ${GITIGNORE}"
