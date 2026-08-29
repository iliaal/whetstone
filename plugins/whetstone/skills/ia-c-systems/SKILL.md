---
name: ia-c-systems
class: language
description: >-
  C patterns for systems code, libraries, and native extensions: module
  layout, function decomposition, status-enum errors, memory safety, undefined
  behavior, and performance measurement. Use when writing, reviewing,
  refactoring, or debugging C, working with malloc lifetimes, buffer
  overflows, sanitizers, or Valgrind, or building native extensions. For C++,
  see ia-cpp-systems.
paths: "**/*.c,**/*.h"
---

# C Systems & Native Code

Covers C11 and later for libraries, systems code, and native extensions. For C++ (RAII, templates, move semantics), see the `ia-cpp-systems` skill.

## Repo conventions outrank this skill

Read the repo's `AGENTS.md`/`CLAUDE.md`, its public headers, and two adjacent `.c` files before writing anything. Where they conflict with the rules below, they win, and the diff carries no note about it.

This gate is load-bearing. Established C codebases sanction idioms these rules would otherwise flag:

| Local idiom | Where it is correct |
|---|---|
| Tab indentation | php-src and its extensions, Linux kernel |
| `goto cleanup` / `goto err` | Kernel, OpenSSL, curl, php-src: the dominant multi-resource release idiom |
| Macros containing `return` | `RETURN_*`/`RETVAL_*` in PHP extensions, `Py_RETURN_*` in CPython |
| Project status types | `zend_result`, `CURLcode`, `int` plus `errno`: do not invent a parallel enum beside one |

Never widen a scoped task into a repo-wide restyle because adjacent untouched C predates a rule here.

**When the target is a PHP extension** (`php_*.h`, `PHP_FUNCTION`, `zend_`, `config.m4`), load [php-extension-c.md](./references/php-extension-c.md) before applying any rule below. Layout, macros, the error model, memory, and assertions all carry extension-specific overrides, and the memory one in particular inverts the base guidance: extensions use a request-scoped allocator, not `malloc`/`free`.

## Tooling

| Tool | Purpose |
|------|---------|
| `gcc` / `clang` | `-Wall -Wextra -Werror -Wconversion -Wshadow` from the first commit on a new project; on an existing tree, the repo's profile plus zero *newly introduced* warnings |
| ASan + UBSan | `-fsanitize=address,undefined -fno-omit-frame-pointer`: default for test builds |
| `valgrind --leak-check=full` | Leak and uninitialized-read detection where ASan cannot be linked |
| `clang-tidy` | Lint (`bugprone-*`, `cert-*`, `clang-analyzer-*`) |
| `cppcheck` | Second opinion; catches different classes than clang-tidy |
| `gdb` / `lldb` | `bt full`, `p *ptr`, watchpoints on corrupted fields |
| `clang-format` | Formatter, driven by the repo's `.clang-format`, never a personal preference |

Compiler warnings are the cheapest static analysis available, and a build nobody can get clean has no signal left in it. Turning `-Wconversion` or `-Werror` on globally over a mature tree produces thousands of unrelated failures, so raise the bar on the diff rather than the repository unless the whole codebase is in scope.

- A faulting load with a base register and a displacement is a field access, so name the field by counting the struct's offsets by hand with alignment and padding respected, and classify the base register against null, kernel space, the heap range, and the neighbourhood of the stack pointer. A non-null heap-shaped base whose displacement lands on unmapped memory fits both "the caller passed null" and "the object was freed between creation and use", and the fix that re-derives the pointer from a live anchor closes both, so prefer it over reproducing the exact trigger.

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
- Every `switch` case ends in `break` or an explicit `/* fallthrough */`. Require `default` when switching on an open-ended integer or an externally supplied value. On a closed internal enum, prefer *omitting* `default` with `-Wswitch-enum` enabled, because that is what makes adding an enumerator produce a warning at every switch that needs updating; a `default` silences exactly the diagnostic worth having. If the control flow needs proving, add a real `assert(0)`, never an unreachable annotation (see the UB table in [memory-safety.md](./references/memory-safety.md) for why). The consequence worth carrying here: because reaching one is UB rather than a diagnostic, a bug filed as "assertion failure on a debug build" is usually also a live user-visible bug on stock release builds, wearing a completely different symptom.
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

## Boundaries and assertions

Public entry points validate arguments and return the argument-error status. Internal statics do not re-validate; they `assert` their invariants instead. Every state-mutating leaf asserts at least one invariant.

An assert is a machine-checked comment: it states what must stay true and sits exactly where an editor is about to change something. Standard `assert` costs nothing in builds that define `NDEBUG` before including `<assert.h>`, which is a project decision rather than an automatic property of a release build. Where assertions stay enabled in production, assert meaningful invariants and stop chasing density. Validation duplicated at every level is noise that hides logic.

Check what a **project's own** assert macro degrades to before assuming it is free. A macro that becomes an *assume* rather than a no-op still evaluates its condition on some toolchains: clang's `__builtin_assume` and MSVC's `__assume` do not evaluate, but the GCC `__builtin_expect` plus `__builtin_unreachable` form does. So an assert whose condition calls a function in another translation unit emits a real call in a release build, silently paying back the check an optimization just removed, and it measures perfectly on clang while regressing on GCC. Wrap those in the project's debug-only conditional instead. Do not answer that by marking the called predicate `pure` so the optimizer can drop it. The attribute is a promise to every caller, not a local hint, and it licenses common-subexpression elimination across exactly the state changes a context-dependent predicate exists to observe.

## Macros

Uppercase names, every argument and the whole body parenthesized, multi-statement bodies in `do { } while (0)`. No macro evaluates an argument twice. Prefer `static inline` wherever types allow.

Hidden control flow inside a macro makes visible code lie about its own paths, so a macro containing `return`, `goto`, `break`, or `continue` is banned unless the project already sanctions one. Where a project has none and unchecked calls are a recurring bug, a single `MODULE_TRY(expr)` beside the status enum is a defensible exception, restricted to functions that acquire nothing. Adding a second hidden-return mechanism to a codebase that already has one is a net loss.

## Memory and lifetime

State ownership at the interface, in the name (`_create` vs `_init`) and in the contract comment. Treat allocation failure as a status, never an abort, outside `main`.

For sanitizer invocation, the integer overflow and truncation rules, allocation and lifetime patterns, the recursion-to-worklist conversion, and untrusted-input parsing discipline, load [memory-safety.md](./references/memory-safety.md).

## Correctness traps

Four shapes compile clean, pass review, and fail in production. Check for them by name:

| The code does this | The trap |
|---|---|
| Formats a number another program parses | The `printf` float family follows process-global `LC_NUMERIC`; one `setlocale` anywhere emits `12,5` into SVG or JSON |
| Reads from a stream | Short reads are normal, and `&buf[n]` on a typed pointer advances `n * sizeof(*buf)` |
| Derives a range from user input | `end = start + count - 1` overflows before the validation that would reject it |
| Passes an integer to a foreign API | A value that passes a sign check still narrows to something else |

Load [correctness-traps.md](./references/correctness-traps.md) for detection greps, fix patterns, macro shadowing, and the portability checklist.

## Testing

C has no dominant framework, so follow the repo's: Unity, Check, CMocka, Criterion, or plain assert-and-exit driven by the build. Whichever it is, run the suite under `-fsanitize=address,undefined` in CI, and make each new test fail against the unfixed code before accepting it.

- A quarantined test is a memory-safety blind spot, not a compatibility note. Whatever a skipped or expected-fail case exercises stops being watched by the sanitizer lane for as long as the skip lasts, and its label was written by whoever quarantined it, usually from a glance, so "known leak" is the standing guess for anything that merely looked wrong about memory. Re-run every skipped test touching lifetimes, ownership, or teardown under the instrumented build before trusting its label, and when one turns out to be a real fault, move it into the instrumented suite rather than leaving it skipped.

For generic test discipline (anti-patterns, real assertions, rationalization resistance), see the `ia-writing-tests` skill.

## Trusting the build

A verification result is a claim about a binary, not about a diff, and the two separate quietly.

- A failing test in untouched, correct-reading code: rebuild from clean before debugging (stale-artifact procedure: the `ia-debugging` skill's specialized-patterns reference).
- An incremental build can exit zero, echo the compile line for the file just edited, and still skip the link. Compare the artifact's timestamp against every source touched this session; neither the exit code nor the echoed command proves the binary changed. A result that matches the pre-edit behavior exactly is the tell, and forcing the rebuild sometimes surfaces a compile error the stale artifact had been hiding.
- Never take a copy of a configured tree as the second variant of a comparison. Dependency files written by the configure step hold absolute paths into the original tree, so the copy's build evaluates prerequisites against files nobody edited, compiles nothing, and links an artifact differing only in build metadata. Take a fresh checkout and re-run configure per variant, and confirm the change is actually present with one cheap behavioral probe, or an observable side channel such as an output size, before spending time measuring.
- A `CFLAGS=` handed to a configure script that inherits its base flags from elsewhere replaces them rather than appending, which silently drops the optimization level and produces a large unexplained regression from a flag that could not cause one. Keep the level explicit when adding a flag, and grep the generated makefile for it before believing any number the build produced.

## Measuring a change

- Never measure on a sanitizer or debug build. It inflates absolute time several-fold, which everyone remembers, and it distorts the ratio between implementations, which they do not: the per-access and per-allocation overhead falls hardest on allocation-heavy code, so a comparison against a differently-shaped competitor reads far better than it is. Worse, it systematically over-rewards the entire class of micro-optimization whose theory is "fewer allocation or append calls", which is how a genuine regression ships as a measured win. The sign flips on a release non-debug build, so check the optimization level too, not only the absence of a sanitizer.
- Interleave the two variants per round and carry a case the change cannot reach. A uniform move across untouched code is the harness, not the code: on a machine with mixed core types, one variant's heavy cases leave the core throttled for the other's, and run-to-run spread for a single unchanged binary reaches double digits where a quiet machine gives a few tenths of a percent. The failure does not look noisy; it is a clean table of consistent wrong numbers.
- A number stored from an earlier session is a different variant. Rebuild the old binary and measure it alongside the new one, because the comparison is what goes wrong, not either measurement.
- Instruction counts are deterministic and immune to frequency and core type, so use them to reject a candidate cheaply and to bound a claimed win, never to assert one: a removed load plus a predicted branch retires nearly free. Read a zero delta as "this instrument cannot see this change", which is the correct reading for anything that only alters allocation timing or buffer headroom.
- A measured win on a path the diff cannot reach is code layout, not the change. Confirm it on a second architecture, or rebuild the baseline with alignment flags only and watch the same case move by the same amount. Layout differences are deterministic per binary, so they produce large stable effects that survive any amount of repetition, and the resulting confidence is entirely misplaced.
- Removing instructions the processor was already hiding is context-fragile; removing repeated work from the always-executed path survives context. An isolated tight loop keeps the branch predictor trained and the working set resident, so it overstates the first kind and can overstate the ceiling of a hotspot that is not addressable at all. Validate in a realistic mixed workload before believing either.
- `__attribute__((optimize(...)))` is an inlining barrier, not a per-function optimization knob: the attributed function is not inlined into its callers and they are not inlined into it. It can isolate an optimization level for a self-contained local loop, cannot capture any win that depended on inlining, and pinning a hot function below its translation unit's level inserts a call wall that regresses past a uniform build at either level. Use a separate translation unit compiled at the other level.

## Refactoring existing C

Short, flat, guarded, and free of magic numbers is not the same as done. Before accepting an existing function, run the near-miss test: duplicated mutation, data encoded as control flow, interleaved concepts, declarations sitting above their first valid value.

Judge any proposed refactor by the cost of the next change, not by line count. For the full three-stage worked example with its change-cost proof, and the deeper normative rules behind the sections above, load [legibility-standard.md](./references/legibility-standard.md).

## Discipline

- Preserve behavior and ABI unless a semantic change was requested. Use an adapter when a foreign API conflicts with a local rule.
- When a required constraint forces a deviation, comment at the deviation site and state the constraint. A note in the delivery message does not replace a comment in the source.
- A frozen public signature that cannot return a status excuses the status rule and nothing else: internal asserts and every other locally satisfiable rule still apply.
- Relocating a fix from a call site into a shared helper widens the set of struct fields that helper reads, and every caller that satisfied the old contract by accident, by leaving a now-read field uninitialized, becomes a fresh bug. Audit all callers when a shared function starts reading a new field, not only the one that motivated the change; an initialization assert on the aggregate is a debug check, not a guarantee that callers zero every member.
- Do not claim compliance for checks that could not run. Name the command that did not execute.

## Verify

- Build passes under the repo's warning profile with zero newly introduced warnings (greenfield: the full `-Wall -Wextra -Werror -Wconversion -Wshadow` bundle, zero warnings)
- Test suite passes under `-fsanitize=address,undefined` with zero reports
- `valgrind --leak-check=full --error-exitcode=1` clean where the suite links under it
- Every new fallible call site checked; every new error value traced to one producer
- Every new state-mutating leaf carries an assert
- No new `goto` outside the repo's sanctioned form or the single-forward-jump cleanup; no recursion over external input; no loop over external input without a named bound
