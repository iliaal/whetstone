#!/usr/bin/env bash
# init-plan.sh — Scaffold a durable task plan
# Usage: bash init-plan.sh [task-name] [--force]
#
# Creates .plan/task_plan.md
# Adds .plan/ to .gitignore if not present
# Refuses to overwrite a task_plan.md that still has unchecked tasks
# unless --force is given.

set -euo pipefail

PLAN_DIR=".plan"
FORCE=0
TASK_NAME="Unnamed Task"
for arg in "$@"; do
    case "$arg" in
        --force) FORCE=1 ;;
        *) TASK_NAME="$arg" ;;
    esac
done
DATE=$(date +%Y-%m-%d)

# Guard: an existing plan with unchecked tasks is live work in progress.
if [ "$FORCE" -ne 1 ] && [ -f "$PLAN_DIR/task_plan.md" ] && grep -q '^\s*- \[ \]' "$PLAN_DIR/task_plan.md"; then
    echo "ERROR: $PLAN_DIR/task_plan.md has unchecked tasks." >&2
    echo "Same work continuing: update it in place. Different work: confirm which plan wins, then re-run with --force." >&2
    exit 1
fi

# Create directory
mkdir -p "$PLAN_DIR"

# Add to .gitignore if not present
if [ -f .gitignore ]; then
    grep -qxF '.plan/' .gitignore 2>/dev/null || echo '.plan/' >> .gitignore
else
    echo '.plan/' > .gitignore
fi

# task_plan.md
cat > "$PLAN_DIR/task_plan.md" << EOF
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

echo "Created ${PLAN_DIR}/ with:"
echo "  - task_plan.md"
echo "Added .plan/ to .gitignore"
