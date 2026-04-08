---
name: simplifying-code
description: >-
  Simplifies, polishes, and declutters code without changing behavior. Use when
  asked to simplify, clean up, refactor, declutter, remove dead code or AI slop,
  or improve readability. For analysis-only reports without code changes, use
  code-simplicity-reviewer agent.
---

# Simplifying Code

## Principles

| Principle | Rule |
|-----------|------|
| **Preserve behavior** | Output must do exactly what the input did -- no silent feature additions or removals. Specifically preserve: async/sync boundaries (do not convert sync to async or reverse), error propagation paths (do not alter strategy), logging/telemetry/guards/retries that encode operational intent, and domain-specific steps (do not collapse into generic helpers that hide intent) |
| **Explicit over clever** | Prefer explicit variables over nested expressions. Readable beats compact |
| **Simplicity over cleanliness** | Prefer straightforward code over pattern-heavy "clean" code. Three similar lines beat a premature abstraction |
| **Surgical changes** | Touch only what needs simplifying. Match existing style, naming conventions, and formatting of the surrounding code |
| **Surface assumptions** | Before changing a block, identify what imports it, what it imports, and what tests cover it. Edit dependents in the same pass |

## Process

1. **Read first** -- understand the full file and its dependents before changing anything. Apply Chesterton's Fence: if you see code that looks unnecessary but don't understand why it's there, check `git blame` before removing it. First understand the reason, then decide if the reason still applies.
2. **Identify invariants** -- what must stay the same? Public API, return types, side effects, error behavior
3. **Identify targets** -- find the highest-impact simplification opportunities. Impact = readability and maintainability; prioritize: control flow -> naming -> duplication -> types (see Smell -> Fix table)
4. **Apply in order** -- control flow → naming → duplication → data shaping → types. Structural changes first, cosmetic last
5. **Verify** -- confirm no behavior change: tests pass, types check, imports resolve

## Smell → Fix

| Smell | Fix |
|-------|-----|
| Deep nesting (>2 levels) | Guard clauses with early returns |
| Long function (>20 lines) | Extract into named functions by responsibility |
| Too many parameters (>3) | Group into an options/config object |
| Duplicated block (**3+** occurrences) | Extract shared function. Two copies = leave inline; wait for the third |
| Magic numbers/strings | Named constants |
| Complex conditional | Extract to descriptively-named boolean or function |
| Dense transform chain (3+ chained methods) | Break into named intermediates for debuggability |
| Dead code / unreachable branches | Delete entirely -- no commented-out code |
| Unnecessary `else` after return | Remove `else`, dedent |

## AI Slop Removal

When simplifying AI-generated code, specifically target:

- **Redundant comments** that restate the code (`// increment counter` above `counter++`) -- delete them
- **Unnecessary defensive checks** for conditions that cannot occur in context -- remove the guard
- **Gratuitous type casts** (`as any`, `as unknown as T`) -- fix the actual type or use a proper generic
- **Over-abstraction** (factory for 2 objects, wrapper around a single call, util file with 1 function) -- inline the code
- **Inconsistent style** that drifts from the file's existing conventions -- match the file
- **Placeholder stubs** (`// ...`, `// rest of code`, `// similar to above`, `// continue pattern`, `// add more as needed`) -- leave unsimplified code as-is rather than replacing it with stubs
- **Redundant error wrapping** (`catch(e) { throw e; }`, `catch(e) { throw new Error(e.message); }`) that strips the original stack for no reason -- remove the try/catch entirely and let errors propagate
- **Verbose stdlib reimplementations** (hand-rolled loops that replicate `array_filter`, `Array.from`, `Collection::pluck()`, `itertools`) -- replace with the stdlib/framework one-liner

## Stop Conditions

Stop and ask before proceeding when:
- Simplification requires changing a public API (function signatures, return types, exports)
- Behavior parity cannot be verified (no tests exist and behavior is non-obvious)
- Code is intentionally complex for domain reasons (performance-critical, protocol compliance)
- Scope implies a redesign rather than a simplification

## Constraints

- Only simplify what was requested -- do not add features, expand scope, or introduce new dependencies
- Leave unchanged code untouched -- do not add comments, docstrings, or type annotations to lines that were not simplified
- Do not bundle unrelated cleanups into one patch -- each simplification should be a coherent, reviewable unit
- Do not introduce framework-wide patterns while simplifying a small local change
- Do not replace understandable duplication with opaque utility layers -- three similar lines are better than a premature abstraction
- Keep comments that explain intent, invariants, or non-obvious constraints. Remove comments that restate obvious code behavior.
- If a simplification would make the code harder to understand, skip it
- Watch for over-simplification: inlining too aggressively removes names that gave concepts meaning; combining unrelated logic into one function hides distinct responsibilities; removing abstractions that exist for testability breaks the test suite
- When unsure whether a block is dead code, ask instead of deleting

## Verify

- Tests pass and types check after changes
- No behavior change (same inputs produce same outputs)
- Scope limited to requested files -- no drive-by cleanups

## Integration

- `code-simplicity-reviewer` agent -- analysis-only pass producing a simplification report (no code changes). Use before refactoring to identify targets.

## Output

After simplifying, report:
- **Scope touched**: files and functions modified
- **Key simplifications**: what changed and why (one line each)
- **Verification**: tests pass, types check, no behavior change
- **Residual risks**: assumptions made, areas not touched that may need attention
