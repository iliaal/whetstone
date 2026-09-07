# Implementation structure

## File and module layout

Every `.c` file in this order: file comment naming what the module owns; system includes, blank line, project includes; constants (enums first, `#define` for strings and conditional compilation only); types; prototypes for every static function, each with its contract comment; public definitions in header order; static definitions in call order.

Every `.h`: include guard, includes, constants, types, prototypes. What a header must not carry is a *definition* with external or tentative linkage, meaning a non-inline function body or a variable that allocates storage. A `static inline` definition is fine and is the only way to publish one; an `extern` declaration is fine and is sometimes required.

A reader who finishes the first screen holds the module's complete vocabulary and never meets an unresolved symbol.


## Naming

- Module prefix on every symbol with external linkage, and on statics too: `rb_push`, `net_send`.
- Functions are verb_object. Predicates start `is_`/`has_` and are never negated: `is_valid`, not `is_not_ready`.
- Lifetime pairs are exact and carry meaning: `_create`/`_destroy` implies heap allocation with ownership transfer, `_init`/`_deinit` implies caller-owned storage, `_open`/`_close`.
- Precise beats verbose: `retry_count`, not `number_of_connection_retry_attempts`.
- Name length scales with the distance between declaration and last use. `i` is fine in a five-line loop; anything crossing 20 lines gets a real name.
- Units live in the name: `TIMEOUT_MS`, `MAX_PAYLOAD_BYTES`.

Naming is the primary navigation channel for both greps and models, not decoration. A magic number is a fact with no grep anchor; a named constant is editable in exactly one place.


## Functions

Apply the name test **first**, before any decomposition rule below: if the most honest name for a candidate helper merely paraphrases its body, inline it and stop. A helper earns existence by naming a concept, owning an error value, or isolating a side effect. Nothing else counts.

Having passed it:

- One job per function. A contract comment needing the word "and" means two functions.
- Target 15 lines, hard cap 40. Nesting depth 2. Guard clauses first, happy path at the left margin.
- Parameter order: context pointer, outputs, pure inputs. A buffer and its length stay adjacent, buffer first. Past 4 parameters, the list is a struct trying to exist.
- No static locals except `static const` lookup tables.
- Classify every function as orchestrator (helper calls, status checks, branches on named predicates), leaf (straight-line logic calling only accessors and pure utilities), or adapter (wraps exactly one foreign call and translates its convention). Never a mix. Public visibility is a separate axis, not a fourth altitude.


## Control flow

- Early return over else chains.
- `goto` only where the repo sanctions it, or for one forward jump to one cleanup label when three or more interdependent resources are live. A `goto` whose label only returns is indirection buying nothing.
- Every `switch` case ends in `break` or an explicit `/* fallthrough */`. Require `default` when switching on an open-ended integer or an externally supplied value. On a closed internal enum, prefer *omitting* `default` with `-Wswitch-enum` enabled, because that is what makes adding an enumerator produce a warning at every switch that needs updating; a `default` silences exactly the diagnostic worth having. If the control flow needs proving, add a real `assert(0)`, never an unreachable annotation (see the UB table in [memory-safety.md](./memory-safety.md) for why). The consequence worth carrying here: because reaching one is UB rather than a diagnostic, a bug filed as "assertion failure on a debug build" is usually also a live user-visible bug on stock release builds, wearing a completely different symptom. A foreign library's enum is the opposite case, since the compiler cannot warn about members it was never shown: a `default` arm returning a plausible value such as null or zero turns every member the switch forgot into silent data loss, so make that arm fail loudly and re-enumerate the foreign enum against the switch on every dependency upgrade.
- A loop body over 10 lines becomes a named function.
- Give an explicit named bound to every loop whose trip count comes from untrusted or externally-supplied data. Traversals bounded by a structure's own size invariant (`while (fgets(...))`, a list walk, a scan to a terminator) do not need one; name the invariant in a comment or an assert instead. A deliberate event pump carries a comment saying exactly that.
- No recursion over externally-supplied input. Convert to a loop over an explicit bounded worklist: stack depth becomes visible and termination checkable. Unbounded recursion over attacker-controlled nesting is a live CVE class in parsers and serializers.
- No side effects inside conditions. No assignment inside `if`. No nested ternaries.


## Errors

- Every fallible function returns a status. Adopt the project's type if one exists; otherwise one enum per module, success 0 and named (`RB_OK`), values prefixed (`RB_ERR_ALLOC`).
- Never return `bool` from anything that can fail more than one way.
- Never mix errno-style and enum-style inside module code. Wrap libc at the boundary and convert once.
- Every fallible call is checked. Status propagates upward unchanged; only the top of the chain logs, converts, or decides.
- Minimize producers per error value. `grep RB_ERR_FULL` landing on one producing line turns a failure report into a location.


## Types and data

- Pick the type from the value's domain. Exact-width types (`uint32_t`, `int64_t`) where the representation is externally fixed: wire formats, file layouts, registers, exact modular arithmetic. `size_t` for object sizes, counts, and indices; `ptrdiff_t` for pointer differences. Ordinary `int` is correct for an ordinary counter or status whose guaranteed range suffices, and churning established `int` usage to exact-width changes ABI and warning behavior for nothing.
- `const` on every pointer parameter not written through.
- Initialize every object at declaration, and declare it at the smallest scope and the latest point where its first value is already valid.
- One level of dereference per expression. `a->b->c->d` smuggles three lifetimes and three nullability questions into one term; bind intermediates.
- Every union carries a tag. Structs use designated initializers, and any invariant tying two fields together is stated in a comment above the struct.
- Function pointers belong in `static const` dispatch tables, or as a documented callback parameter (a `qsort` comparator, a visitor walk). What to avoid is a function pointer stored loose in mutable state, where the reachable targets cannot be enumerated from the code.


## Macros

Uppercase names, every argument and the whole body parenthesized, multi-statement bodies in `do { } while (0)`. No macro evaluates an argument twice. Prefer `static inline` wherever types allow.

Hidden control flow inside a macro makes visible code lie about its own paths, so a macro containing `return`, `goto`, `break`, or `continue` is banned unless the project already sanctions one. Where a project has none and unchecked calls are a recurring bug, a single `MODULE_TRY(expr)` beside the status enum is a defensible exception, restricted to functions that acquire nothing. Adding a second hidden-return mechanism to a codebase that already has one is a net loss.


## Refactoring existing C

Short, flat, guarded, and free of magic numbers is not the same as done. Before accepting an existing function, run the near-miss test: duplicated mutation, data encoded as control flow, interleaved concepts, declarations sitting above their first valid value.

Judge any proposed refactor by the cost of the next change, not by line count. For the full three-stage worked example with its change-cost proof, and the deeper normative rules behind the sections above, load [legibility-standard.md](./legibility-standard.md).
