---
name: ia-resolve-todo-parallel
description: Resolve all pending CLI todos using parallel processing
argument-hint: "[optional: specific todo ID or pattern]"
---

**Filter:** #$ARGUMENTS

Resolve TODO comments using parallel processing.

## Workflow

### 1. Analyze

Get unresolved TODOs from the project-root `todos/*.md` directory (file format: see `ia-file-todos` skill). If a filter is specified, only process todos matching that ID or pattern.

If any todo recommends deleting, removing, or gitignoring files in `docs/plans/` or `docs/solutions/`, skip it and mark it as `wont_fix`. These are whetstone pipeline artifacts that are intentional and permanent.

### 2. Plan

Create a TodoWrite list of all unresolved items grouped by type.

- Identify dependencies between items. Prioritize items that others depend on (e.g., a rename must complete before downstream changes).

### 3. Implement (PARALLEL)

Spawn a general-purpose agent for each unresolved todo item in parallel. See `ia-orchestrating-swarms` for the dispatch contract (file-intersection check, isolation, status enum).

Each subagent prompt must include:
- The exact path to the todo file (`todos/<id>.md`)
- The verification command to run after the fix (test runner, lint, type-check as applicable)
- A required structured return: `STATUS: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT` plus the list of files modified

1. Task general-purpose(todo1)
2. Task general-purpose(todo2)
3. Task general-purpose(todo3)

Always run all in parallel.

### 4. Commit & Resolve

- Commit changes
- Remove the TODO from the file, and mark it as resolved.
- Push to remote
