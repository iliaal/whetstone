# Concurrency and verification

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

For CMake target design, sanitizer and warning presets, `clang-tidy` configuration (including which checks are fatal versus warn-only), and dependency handling, load [cmake-and-tooling.md](./cmake-and-tooling.md).
