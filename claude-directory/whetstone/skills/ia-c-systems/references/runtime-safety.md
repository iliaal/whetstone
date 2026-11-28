# Runtime safety and interfaces

## Boundaries and assertions

Public entry points validate arguments and return the argument-error status. Internal statics do not re-validate; they `assert` their invariants instead. Every state-mutating leaf asserts at least one invariant.

An assert is a machine-checked comment: it states what must stay true and sits exactly where an editor is about to change something. Standard `assert` costs nothing in builds that define `NDEBUG` before including `<assert.h>`, which is a project decision rather than an automatic property of a release build. Where assertions stay enabled in production, assert meaningful invariants and stop chasing density. Validation duplicated at every level is noise that hides logic.

Check what a **project's own** assert macro degrades to before assuming it is free. A macro that becomes an *assume* rather than a no-op still evaluates its condition on some toolchains: clang's `__builtin_assume` and MSVC's `__assume` do not evaluate, but the GCC `__builtin_expect` plus `__builtin_unreachable` form does. So an assert whose condition calls a function in another translation unit emits a real call in a release build, silently paying back the check an optimization just removed, and it measures perfectly on clang while regressing on GCC. Wrap those in the project's debug-only conditional instead. Do not answer that by marking the called predicate `pure` so the optimizer can drop it. The attribute is a promise to every caller, not a local hint, and it licenses common-subexpression elimination across exactly the state changes a context-dependent predicate exists to observe.

Never discover a foreign container's end by incrementing an index until the accessor returns null. An accessor documented as a plain index may throw or terminate on an out-of-range argument instead of reporting one, so bound every traversal by the API's own count accessor. Bounds-check any index that came from the data as well: a tag byte lifted out of a payload and used to select a child is where untrusted bytes become a structural index.

Constructing a library's objects directly bypasses the validation its high-level path performed. Raw `create_*` constructors skip the range and encoding checks the convenience call made on the way in, so a narrowing constructor wraps silently and a text constructor forces binary through the string encoder. Re-implement those checks when hand-building objects for a bulk path, or keep the convenience path.


## Memory and lifetime

State ownership at the interface, in the name (`_create` vs `_init`) and in the contract comment. Treat allocation failure as a status, never an abort, outside `main`.

For sanitizer invocation, the integer overflow and truncation rules, allocation and lifetime patterns, the recursion-to-worklist conversion, and untrusted-input parsing discipline, load [memory-safety.md](./memory-safety.md).


## Correctness traps

Four shapes compile clean, pass review, and fail in production. Check for them by name:

| The code does this | The trap |
|---|---|
| Formats a number another program parses | The `printf` float family follows process-global `LC_NUMERIC`; one `setlocale` anywhere emits `12,5` into SVG or JSON |
| Reads from a stream | Short reads are normal, and `&buf[n]` on a typed pointer advances `n * sizeof(*buf)` |
| Derives a range from user input | `end = start + count - 1` overflows before the validation that would reject it |
| Passes an integer to a foreign API | A value that passes a sign check still narrows to something else |

Load [correctness-traps.md](./correctness-traps.md) for detection greps, fix patterns, macro shadowing, and the portability checklist.


## Discipline

- Preserve behavior and ABI unless a semantic change was requested. Use an adapter when a foreign API conflicts with a local rule.
- Consume a new flag bit after the existing bitfield members, never ahead of one. Inserting ahead of a published field shifts every following field's position for consumers built against the old header, while `sizeof` and the struct's member offsets stay unchanged, so the usual ABI evidence stays green. Append, and reserve spare bits when publishing a bitfield.
- On a released ABI, new state never goes into a public struct, not even into existing padding: consumers keep the old offsets, and maintainers reject the change regardless of how the layout happens to work out. Take the ladder instead, in order: a file-scope `static` in the using translation unit, a thread-local where the state is per-thread, an encoding into an existing field that the owner sanctions, or the next ABI-breaking branch. Audit the diff against the public headers of a stable branch before proposing it.
- When a required constraint forces a deviation, comment at the deviation site and state the constraint. A note in the delivery message does not replace a comment in the source.
- A frozen public signature that cannot return a status excuses the status rule and nothing else: internal asserts and every other locally satisfiable rule still apply.
- Relocating a fix from a call site into a shared helper widens the set of struct fields that helper reads, and every caller that satisfied the old contract by accident, by leaving a now-read field uninitialized, becomes a fresh bug. Audit all callers when a shared function starts reading a new field, not only the one that motivated the change; an initialization assert on the aggregate is a debug check, not a guarantee that callers zero every member.
- A fork that diverged on its data model cannot be merged from upstream, only cherry-picked into. Once the two trees disagree on field types, a pointer and length against an owned string or an enum against a narrow int, a three-way merge has no conflict to report: it resolves by picking one side and invalidates the other side's assumptions in every consumer. The dangerous part is an accessor that still compiles because both sides declare a member of that name. Port fixes by hand into the fork's shapes, and record each as a local patch naming its upstream origin.
- Do not claim compliance for checks that could not run. Name the command that did not execute.
