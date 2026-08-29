#!/usr/bin/env bash
# init-plan.sh — Scaffold .plan/ directory with template files
# Usage: bash init-plan.sh [task-name] [--force]
#
# Creates .plan/ with task_plan.md, findings.md, progress.md
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
**Files**: [specific files, max 5-8 per phase]

**Tasks**:
- [ ] [Verb-first atomic task]

**Verify**: [specific test command or assertion]
**Exit**: [clear done definition]

## Open Questions

- [Max 3, only truly blocking unknowns]

## Error Log

| Attempt | What Failed | Why | Next Action |
|---------|-------------|-----|-------------|
EOF

# findings.md
cat > "$PLAN_DIR/findings.md" << EOF
# Findings: ${TASK_NAME}

**Created:** ${DATE}

## Architecture

[Key structural observations about the codebase]

## Dependencies

[External dependencies, version constraints, gotchas]

## Discoveries

[Anything unexpected found during investigation]
EOF

# progress.md
cat > "$PLAN_DIR/progress.md" << EOF
# Progress: ${TASK_NAME}

**Started:** ${DATE}

## Session Log

### ${DATE}

- [Started planning]

## Files Changed

| File | Change |
|------|--------|

## Test Results

| Phase | Command | Result |
|-------|---------|--------|
EOF

echo "Created ${PLAN_DIR}/ with:"
echo "  - task_plan.md"
echo "  - findings.md"
echo "  - progress.md"
echo "Added .plan/ to .gitignore"
