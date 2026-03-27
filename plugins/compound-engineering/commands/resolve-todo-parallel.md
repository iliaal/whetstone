---
name: resolve-todo-parallel
description: Resolve all pending CLI todos using parallel processing
argument-hint: "[optional: specific todo ID or pattern]"
---

**Filter:** #$ARGUMENTS

Resolve TODO comments using parallel processing.

## Workflow

### 1. Analyze

Get unresolved TODOs from the /todos/\*.md directory. If a filter is specified, only process todos matching that ID or pattern.

If any todo recommends deleting, removing, or gitignoring files in `docs/plans/` or `docs/solutions/`, skip it and mark it as `wont_fix`. These are compound-engineering pipeline artifacts that are intentional and permanent.

### 2. Plan

Create a TodoWrite list of all unresolved items grouped by type.

- Identify dependencies between items. Prioritize items that others depend on (e.g., a rename must complete before downstream changes).
- Output a mermaid flow diagram showing execution order: which items can run in parallel, which must run sequentially.
- Use the diagram to determine the spawn order in step 3.

### 3. Implement (PARALLEL)

Spawn a general-purpose agent for each unresolved todo item in parallel:

1. Task general-purpose(todo1)
2. Task general-purpose(todo2)
3. Task general-purpose(todo3)

Always run all in parallel.

### 4. Commit & Resolve

- Commit changes
- Remove the TODO from the file, and mark it as resolved.
- Push to remote
