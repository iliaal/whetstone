# Simplification patterns

## Smell → Fix

| Smell | Fix |
|-------|-----|
| Deep nesting (>2 levels) | Guard clauses with early returns |
| Long function (>20 lines) | Extract into named functions by responsibility |
| Too many parameters (>3) | Group into an options/config object |
| Duplicated block (**3+** occurrences) | Extract shared function. Two copies = leave inline; wait for the third |
| Magic numbers/strings | Named constants |
| Complex conditional | Extract to descriptively-named boolean or function |
| Boolean-returning `if/else` (each branch returns a literal `True`/`False`) | Preserve the boolean return type and truthiness evaluation: in Python use `return True if a and b else False`; use `return a and b` only when both operands are guaranteed booleans |
| Dense transform chain (3+ chained methods) | Break into named intermediates for debuggability |
| Dead code / unreachable branches | Delete entirely; no commented-out code |
| Unnecessary `else` after return | Remove `else`, dedent |


## AI Slop Removal

When simplifying AI-generated code, specifically target:

- **Redundant comments** that restate the code (`// increment counter` above `counter++`): delete them
- **Unnecessary defensive checks** for conditions that cannot occur in context: remove the guard. Where the guard, retry, workaround, or flag counters an *external* hazard (a harness default, an upstream bug, a race, a platform quirk), "cannot occur" needs evidence: demonstrate the hazard's precondition is present and handled. A green suite is not that evidence when the run may never have triggered the hazard at all; absence of failure and absence of the hazard look identical from the outside. If the precondition cannot be reproduced, keep the code and record the gap. Guards against conditions the type system already excludes need no such proof, provided the type is enforced at that boundary rather than merely declared; deserialized payloads, unchecked API responses, and anything reached through a cast or assertion do not qualify
- **Gratuitous type casts** (`as any`, `as unknown as T`): fix the actual type or use a proper generic
- **Over-abstraction** (factory for 2 objects, wrapper around a single call, util file with 1 function): inline the code
- **Inconsistent style** that drifts from the file's existing conventions: match the file
- **Placeholder stubs** (`// ...`, `// rest of code`, `// similar to above`, `// continue pattern`, `// add more as needed`): leave unsimplified code as-is rather than replacing it with stubs
- **Redundant error wrapping** (`catch(e) { throw e; }`, `catch(e) { throw new Error(e.message); }`) that strips the original stack for no reason: remove the try/catch entirely and let errors propagate
- **Verbose stdlib reimplementations** (hand-rolled loops that replicate `array_filter`, `Array.from`, `Collection::pluck()`, `itertools`): replace with the stdlib/framework one-liner, but verify edge-case parity first: empty input, null/None guard, no-match default, zero-value path. The one-liner can silently differ from the loop (an empty-input crash, a missing no-match default, lost ordering); a structurally cleaner version that changes behavior on an edge case is not a simplification
- **Hand-maintained guarantees** the platform, framework, or a downstream layer already enforces (a manual retry wrapping a client that already retries, a hand-rolled TTL cache the ORM/query layer already provides, manual null-coalescing on a value the contract guarantees non-null): name the layer that owns the guarantee and what the code collapses to without it. Remove only when it preserves every output, error, side-effect, and ordering; cite the test or a direct comparison proving equivalence, since "it's already guaranteed" over-fires easily
- **Copy-paste with variation**: before proposing a shared abstraction, check whether the duplicated construct can be *eliminated* by deriving it from an existing source of truth (a constant, an existing map, a generated value). Consolidate into a helper only when elimination isn't behavior-preserving *and* the duplication has already cleared the 3-occurrence gate (Smell → Fix); below that, leave it inline per Constraints
