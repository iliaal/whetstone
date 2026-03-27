---
name: resolve_todo_parallel
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

Create a TodoWrite list of all unresolved items grouped by type.Make sure to look at dependencies that might occur and prioritize the ones needed by others. For example, if you need to change a name, you must wait to do the others. Output a mermaid flow diagram showing how we can do this. Can we do everything in parallel? Do we need to do one first that leads to others in parallel? I'll put the to-dos in the mermaid diagram flow‑wise so the agent knows how to proceed in order.

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
