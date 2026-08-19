---
name: ia-cpp-systems
class: language
description: >-
  Modern C++ patterns: RAII and ownership, rule of zero/five, exceptions and
  error handling, API and ABI boundaries, templates, and CMake tooling. Use when
  writing, reviewing, refactoring, or debugging C++, working with smart pointers,
  move semantics, memory leaks, template errors, or gtest. For plain C, see
  ia-c-systems.
paths: "**/*.cpp,**/*.hpp,**/*.cc,**/*.hh,**/*.cxx"
---

# C++ Systems & Libraries

Covers C++17 as the baseline, with C++20 features called out where a project's standard allows them. For plain C (manual lifetimes, status enums, native extensions), see the `ia-c-systems` skill.

## Repo conventions outrank this skill

Check `CMakeLists.txt` for `CXX_STANDARD`, read `.clang-format` and `.clang-tidy`, and read two adjacent translation units before writing. Where they conflict with the rules below, they win.

The conflicts that actually happen:

| Local constraint | Consequence |
|---|---|
| `-fno-exceptions` | Error handling is codes or `expected`-alikes. Constructors cannot report recoverable failure, so use a fallible factory or construct a valid fallback state. `new (std::nothrow)` only where the project's OOM policy is to observe null and recover; plain `new` is fine where the policy is termination |
| Standard pinned below C++17 | No `std::optional`/`string_view`/structured bindings/`if constexpr`; check before using any |
| Public header is ABI-stable | No layout changes, no inline-function changes, no added virtuals: load the ABI reference |
| Embedded or freestanding target | No RTTI, no dynamic allocation in hot paths, possibly no STL containers |

## Tooling

| Tool | Purpose |
|------|---------|
| `cmake` | Build system; `CMAKE_EXPORT_COMPILE_COMMANDS=ON` feeds every other tool |
| `clang-format` | Formatter, driven by the repo's `.clang-format` |
| `clang-tidy` | Lint (`bugprone-*`, `performance-*`, `modernize-*`, `cppcoreguidelines-*`) |
| ASan + UBSan | `-fsanitize=address,undefined`; TSan separately for threaded code |
| `gtest` / `catch2` | Unit tests |
| `include-what-you-use` | Cuts transitive-include creep that slows builds and hides dependencies |
| `ccache` | Compile cache; the single biggest iteration-speed win on a C++ tree |

Build with `-Wall -Wextra -Wpedantic -Wshadow -Wconversion` and treat warnings as errors in CI.

## Ownership and RAII

Every resource has exactly one owner, and that owner is an object whose destructor releases it. A raw `new` or `delete` in application code is a defect.

- `std::unique_ptr<T>` for sole ownership. It is the default; it costs nothing over a raw pointer.
- `std::shared_ptr<T>` only where lifetime is genuinely shared and cannot be expressed as "the owner outlives the users". Reach for it third, not first.
- `std::weak_ptr<T>` to break ownership cycles. LeakSanitizer does report a cycle that is unreachable from any root, but not one still reachable from a global or other registered root, and detection varies by platform and configuration. Do not rely on the sanitizer to find these.
- Raw `T*` and `T&` mean **non-owning observation**, and are correct in that role. A parameter taking `unique_ptr` by value is announcing that it consumes ownership; one taking `T*` is announcing it does not.
- `std::span<T>` (C++20) or a pointer-plus-length pair for a borrowed contiguous range **in a new public API**, since `const std::vector<T>&` there refuses every other container. On a C++17 baseline, or for internal code whose callers all hold vectors anyway, `const std::vector<T>&` is fine and simpler.

**Rule of zero**: a class that owns nothing declares no destructor, no copy, and no move. Composing members that manage themselves gets all five special members correct for free. **Rule of five**: declaring any one of destructor, copy constructor, copy assignment, move constructor, or move assignment obliges the author to reason about all five. A user-declared destructor suppresses the implicit move operations, so a class that gained a destructor silently started deep-copying where it used to move.

## Const correctness and value semantics

- `const` by default on locals, member functions, and reference parameters.
- Pass by value for types that are cheap to move (`std::string`, `std::vector`) when the function stores the argument; pass by `const&` when it only reads. Do not pass by `const&` and then copy inside.
- `std::string_view` for read-only string parameters, with one rule attached: never store one unless the backing buffer is guaranteed to outlive the view. A `string_view` member is a dangling reference waiting for a temporary.
- Mark member functions `const` and `noexcept` where true. `noexcept` on move operations is what lets `std::vector` move rather than copy on reallocation.

## Error handling

Pick one model per module and hold it at the boundary.

- **Exceptions** where the project allows them: throw types deriving from `std::exception`, throw by value, catch by `const&`. Use them for genuinely exceptional conditions, not for control flow.
- **`std::optional<T>`** for "absent is normal". **`std::expected<T, E>`** (C++23) or a project equivalent for "failed with a reason".
- **Error codes** in exception-free builds, with `[[nodiscard]]` on every returning function so an ignored failure is a warning.
- Mark anything that must not throw `noexcept`, and mean it: an escaping exception calls `std::terminate`.
- A constructor that can fail either throws or does not exist. Two-phase `init()` construction produces objects with an invalid state that every method must then check. Prefer a static factory returning `optional`/`expected`.

## API design

The decisions that break callers, learned the expensive way:

- **Three decisions break callers when they go wrong**: `explicit` on a single-argument constructor (decide at introduction, since adding it later is source-breaking), removing an overload (keep the narrow one and delegate), and an overload that silently ignores part of its argument (delete it or `static_assert` instead). Rationale and the full evolution rules are in the reference below.
- Prefer free functions over members where they do not need private access; they extend without touching the class.
- Return by value and let the compiler elide. Out-parameters exist for multiple returns and for reuse of a caller's buffer, not as an optimization.

For `extern "C"` boundaries, exception containment, PIMPL, and ABI-stable headers, load [api-and-abi.md](./references/api-and-abi.md).

## Templates and generic code

Use a template when at least three concrete instantiations exist or are certain. Before that, a concrete type is clearer and compiles faster.

- Constrain with C++20 concepts where available, `static_assert` plus type traits otherwise. An unconstrained template fails deep inside instantiation with an error nobody can read.
- `if constexpr` over tag dispatch and SFINAE where the standard allows it.
- Keep template definitions out of widely-included headers when the instantiation cost is real; explicit instantiation in one translation unit is often the right trade.
- Perfect forwarding (`T&&` plus `std::forward`) only in genuinely forwarding code. A forwarding reference in a constructor hijacks the copy constructor and produces baffling overload resolution.

## Standard library

- Prefer `<algorithm>` and ranges over hand-written loops; a named algorithm states intent that an index loop hides.
- `std::vector` unless measurement says otherwise. `reserve()` when the final size is known.
- Structured bindings for pair and tuple returns; a named struct for anything a caller will read twice.
- Use `std::move` only where the source is genuinely dead afterwards. Never depend on an *unspecified* post-move value; destroy, reassign, or invoke only operations whose post-move contract is documented. Some types do specify one (`unique_ptr` is null, `future` is invalid), and relying on those is fine.
- Never return `std::move(local)`: it defeats copy elision.

## Concurrency

- Lock through an RAII guard, never a bare `lock()`/`unlock()` pair -- an early return or a throw between them leaves the mutex held. `std::lock_guard` for a plain scope, `std::unique_lock` when the lock must be deferred, moved, or handed to a condition variable, `std::shared_lock` for reader access.
- **Name the guard.** `std::lock_guard<std::mutex>{m};` is a temporary that locks and unlocks before the next statement runs, leaving everything after it unguarded, and it compiles silently under `-Wall -Wextra -Wshadow`. `std::lock_guard<std::mutex>(m);` is worse-looking but harmless -- it parses as a declaration of a variable named `m` and fails to compile. Only `std::lock_guard<std::mutex> guard{m};` locks for the scope.
- Take multiple mutexes with one `std::scoped_lock(a, b)` (C++17), which applies a deadlock-avoidance algorithm. Two sequential guards impose a lock order that a second call site can invert.
- Always pass a predicate: `cv.wait(lock, [&]{ return ready; })`. A bare `wait` returns on spurious wakeup and on a notify that raced ahead of the waiter.
- Never call unknown code -- a user callback, a virtual, an observer notification -- while holding a lock. The callee may take another lock, re-enter, or block, and none of that is visible at the call site.
- A `mutex` member makes a class non-copyable and non-movable; decide whether the type is meant to be either before adding one.

Compile-time signal for these is near zero, so run anything threaded under TSan (see Testing) rather than trusting the warning bundle.

## Testing

- gtest is the default (`TEST(Suite, Case)`, `TEST_F` for fixtures). One test file per public surface.
- `EXPECT_*` to continue after failure, `ASSERT_*` where continuing would crash or cascade.
- `EXPECT_THROW`/`EXPECT_NO_THROW` for the exception contract; assert on the exception's type and message, not merely that something threw.
- Run the suite under ASan and UBSan in CI, and under TSan separately for anything threaded.

For generic test discipline (anti-patterns, real assertions, rationalization resistance), see the `ia-writing-tests` skill.

## Build and analysis

For CMake target design, sanitizer and warning presets, `clang-tidy` configuration (including which checks are fatal versus warn-only), and dependency handling, load [cmake-and-tooling.md](./references/cmake-and-tooling.md).

## Legibility

Function decomposition, naming as a greppability contract, the name test that stops over-decomposition, contract comments, and a worked refactor with its change-cost proof: load [legibility-standard.md](./references/legibility-standard.md).

## Discipline

- Preserve behavior and API compatibility unless a break was requested. A public header change is a decision, not a cleanup.
- Do not introduce a template, an inheritance hierarchy, or a policy parameter for a single call site.
- `#include` what the file uses; do not rely on transitive includes from another header.
- No `using namespace` at namespace scope in a header. Fully qualify instead, or scope the `using` to a function body.
- When a constraint forces a deviation, comment at the deviation site and state the constraint.

## Verify

- Build clean with `-Wall -Wextra -Wpedantic -Wshadow -Wconversion -Werror`
- `clang-tidy` reports no new findings on the diff
- Tests pass under `-fsanitize=address,undefined` with zero reports
- Any threaded code touched by the change exercised under TSan with zero reports -- the warning bundle above does not catch lock misuse
- `clang-format --dry-run --Werror` produces no diff
- No new raw `new`/`delete`, no new `shared_ptr` where `unique_ptr` suffices
- Any class that gained a destructor has its move operations reviewed
