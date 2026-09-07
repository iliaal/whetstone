# Build and measurement

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
- Warning suppressions that vendored code needs must not ride the shared flag string. One `CFLAGS` disabling a warning class disables it for first-party code too, and the comment claiming the first-party code is clean without them is unverifiable in the build that carries them. Register vendored sources as their own target with their own flags, and keep the first-party set unsuppressed under `-Werror`.


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
- A call to a function the target platform does not declare is a warning, not an error. The compiler emits an implicit declaration, where an indirection-level or implicit-declaration warning at the assignment is the tell; the linker leaves the symbol undefined in a shared object; and `dlopen` succeeds because resolution is lazy, so the failure arrives as a symbol lookup error the first time that path runs, on the platform CI runs last. Build with `-Werror=implicit-function-declaration` and `-Wl,--no-undefined`, and exercise every conditionally compiled path on the oldest supported platform. Once a tree carries `#ifdef` splits for these calls, a caller added on a POSIX host compiles clean everywhere locally and breaks every Windows lane at once: every lane of one platform failing at compile while the others stay green is that signature, not a flake.
- A shared object is only self-contained on a machine that lacks its dependencies. `-fvisibility=hidden` hides nothing that a vendored header re-exports through its own `visibility("default")` macro, and `-static-libstdc++` and `-static-libgcc` are driver flags the C driver ignores, so a module that loads on the build host fails `dlopen` elsewhere on undefined `std::` or `__cxxabi` symbols. Gate the artifact instead: `nm -D --defined-only` shows no vendor symbols, `nm -D -u` shows no unexpected undefined ones, and the load-and-exercise check runs in a clean minimal container.
- Probe a library capability with a link test, not a header grep. A header newer than the installed library passes the grep and fails at link, and from GCC 14 and Clang 16 onward the implicit declaration is a hard error rather than a warning. Use the link-test macro in every build system the project ships, and where a capability is genuinely unavailable on one platform, state that platform consequence in the release notes.


## Measuring a change

- Never measure on a sanitizer or debug build. It inflates absolute time several-fold, which everyone remembers, and it distorts the ratio between implementations, which they do not: the per-access and per-allocation overhead falls hardest on allocation-heavy code, so a comparison against a differently-shaped competitor reads far better than it is. Worse, it systematically over-rewards the entire class of micro-optimization whose theory is "fewer allocation or append calls", which is how a genuine regression ships as a measured win. The sign flips on a release non-debug build, so check the optimization level too, not only the absence of a sanitizer.
- Interleave the two variants per round and carry a case the change cannot reach. A uniform move across untouched code is the harness, not the code: on a machine with mixed core types, one variant's heavy cases leave the core throttled for the other's, and run-to-run spread for a single unchanged binary reaches double digits where a quiet machine gives a few tenths of a percent. The failure does not look noisy; it is a clean table of consistent wrong numbers.
- A number stored from an earlier session is a different variant. Rebuild the old binary and measure it alongside the new one, because the comparison is what goes wrong, not either measurement.
- Instruction counts are deterministic and immune to frequency and core type, so use them to reject a candidate cheaply and to bound a claimed win, never to assert one: a removed load plus a predicted branch retires nearly free. Read a zero delta as "this instrument cannot see this change", which is the correct reading for anything that only alters allocation timing or buffer headroom.
- A measured win on a path the diff cannot reach is code layout, not the change. Confirm it on a second architecture, or rebuild the baseline with alignment flags only and watch the same case move by the same amount. Layout differences are deterministic per binary, so they produce large stable effects that survive any amount of repetition, and the resulting confidence is entirely misplaced.
- Removing instructions the processor was already hiding is context-fragile; removing repeated work from the always-executed path survives context. An isolated tight loop keeps the branch predictor trained and the working set resident, so it overstates the first kind and can overstate the ceiling of a hotspot that is not addressable at all. Validate in a realistic mixed workload before believing either.
- `__attribute__((optimize(...)))` is an inlining barrier, not a per-function optimization knob: the attributed function is not inlined into its callers and they are not inlined into it. It can isolate an optimization level for a self-contained local loop, cannot capture any win that depended on inlining, and pinning a hot function below its translation unit's level inserts a call wall that regresses past a uniform build at either level. Use a separate translation unit compiled at the other level.
- A/B a compile-time-selected path from one tree by injecting the disable macro through the compiler variable. Gate the `#ifdef` branch behind a single disable token and rebuild with `make CC='cc -DDISABLE_X'`, because re-running configure with a flags variable replaces the base flags, including the optimization level. Confirm from a runtime banner which path each build selected, assert that the two produce identical output, and carry a null control: an operation the gated path cannot reach must move by roughly 0% between the builds.
