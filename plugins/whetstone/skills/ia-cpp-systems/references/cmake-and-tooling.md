# CMake and C++ tooling

Load when setting up or reviewing a C++ build, adding a dependency, wiring sanitizers, or configuring static analysis.

## Target-based CMake

Modern CMake describes targets and their requirements. Directory-scoped commands leak settings into everything below them and are the root of most "works in my build" reports.

| Never | Use instead |
|---|---|
| `include_directories(...)` | `target_include_directories(tgt PUBLIC ...)` |
| `add_definitions(-DFOO)` | `target_compile_definitions(tgt PRIVATE FOO)` |
| appending to `CMAKE_CXX_FLAGS` | `target_compile_options(tgt PRIVATE ...)` |
| `link_directories(...)` | `target_link_libraries(tgt PRIVATE Ns::dep)` |
| `set(CMAKE_CXX_FLAGS "-std=c++17")` | `target_compile_features(tgt PUBLIC cxx_std_17)` |

`PRIVATE` means "I need this to build"; `INTERFACE` means "my consumers need this"; `PUBLIC` is both. Getting these wrong is how an implementation detail becomes part of a library's contract.

```cmake
cmake_minimum_required(VERSION 3.20)
project(mylib LANGUAGES CXX)

find_package(OpenSSL REQUIRED)

add_library(mylib src/client.cpp src/query.cpp)
add_library(Mylib::mylib ALIAS mylib)

target_compile_features(mylib PUBLIC cxx_std_17)
target_include_directories(mylib
    PUBLIC  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
            $<INSTALL_INTERFACE:include>
    PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_link_libraries(mylib PRIVATE OpenSSL::SSL)
```

The generator expressions matter, and they fail loudly rather than subtly: a bare absolute source path in a `PUBLIC` `target_include_directories` makes `install(EXPORT ...)` hard-error with "INTERFACE_INCLUDE_DIRECTORIES property contains path ... which is prefixed in the source directory".

Always export `compile_commands.json`, since clang-tidy, clangd, and IWYU all consume it:

```cmake
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
```

## Warnings as an interface target

Define the warning set once and link it into every target, rather than repeating flags:

```cmake
add_library(project_warnings INTERFACE)
target_compile_options(project_warnings INTERFACE
    "$<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:-Wall;-Wextra;-Wpedantic;-Wshadow;-Wconversion;-Wnon-virtual-dtor;-Wold-style-cast;-Wcast-align>"
    "$<$<CXX_COMPILER_ID:MSVC>:/W4;/permissive->")

target_link_libraries(mylib PRIVATE project_warnings)
```

The quoted, semicolon-separated spelling is the canonical way to carry a flag *list* through a generator expression, and it stays unambiguous wherever the surrounding context handles whitespace differently. (An unquoted, space-separated genex also works in `target_compile_options` and resolves to the same list; the quoted form is the one to reach for by default, not a bug fix.)

Add `-Werror` in CI only. Making it the local default turns every new compiler version into a blocked workday.

## Presets

`CMakePresets.json` replaces the wiki page of build incantations and gives CI and humans the same commands:

```json
{
  "version": 2,
  "configurePresets": [
    {
      "name": "dev",
      "generator": "Ninja",
      "binaryDir": "build/dev",
      "cacheVariables": {
        "CMAKE_BUILD_TYPE": "Debug",
        "CMAKE_EXPORT_COMPILE_COMMANDS": "ON"
      }
    },
    {
      "name": "asan",
      "inherits": "dev",
      "binaryDir": "build/asan",
      "cacheVariables": {
        "CMAKE_CXX_FLAGS": "-fsanitize=address,undefined -fno-omit-frame-pointer -g -O1"
      }
    }
  ],
  "buildPresets": [
    { "name": "dev",  "configurePreset": "dev" },
    { "name": "asan", "configurePreset": "asan" }
  ],
  "testPresets": [
    {
      "name": "asan",
      "configurePreset": "asan",
      "output": { "outputOnFailure": true }
    }
  ]
}
```

`cmake --preset asan && cmake --build --preset asan && ctest --preset asan`.

Two things that bite here. `cmake --build --preset` and `ctest --preset` read `buildPresets` and `testPresets`; a file carrying only `configurePresets` fails with "no such preset" on both. And the schema `version` sets a CMake floor of its own (2 needs 3.20, 3 needs 3.21, 6 needs 3.25) which must not exceed the project's `cmake_minimum_required`.

Sanitizer notes: ASan, TSan, and MSan are mutually exclusive, so each needs its own build directory. UBSan composes with any one of them (`address,undefined`, `thread,undefined`, and `memory,undefined` all link). Set `UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1`, because UBSan otherwise prints diagnostics into a passing test run.

## Dependencies

| Mechanism | When |
|---|---|
| `find_package(Foo REQUIRED)` | The dependency is expected on the system or from a package manager. Default for anything widely packaged. |
| `FetchContent` | Small, source-buildable dependency with no system packaging. Pin a tag or commit, never a branch. |
| Git submodule | The dependency needs local patches, or the build must work fully offline. |

Always consume through a namespaced imported target (`OpenSSL::SSL`, `GTest::gtest_main`). A bare `${FOO_LIBRARIES}` variable carries no include directories, no compile definitions, and no transitive requirements.

## Testing with CTest

```cmake
include(CTest)
find_package(GTest REQUIRED)

add_executable(mylib_ut ut/client_ut.cpp ut/query_ut.cpp)
target_link_libraries(mylib_ut PRIVATE mylib GTest::gtest_main project_warnings)

include(GoogleTest)
gtest_discover_tests(mylib_ut)
```

`gtest_discover_tests` registers each gtest case with CTest individually, so `ctest -R Query` selects real cases and a failure names the case rather than the binary. `add_test` on the whole executable gives one opaque pass/fail.

## Static analysis

`.clang-tidy` at the repo root, applied to changed files rather than the whole tree at first:

```yaml
Checks: >
  bugprone-*,
  cert-*,
  cppcoreguidelines-*,
  modernize-*,
  performance-*,
  readability-*,
  -modernize-use-trailing-return-type,
  -readability-magic-numbers
WarningsAsErrors: 'bugprone-*,cert-*'
HeaderFilterRegex: '^(include|src)/'
```

`HeaderFilterRegex` is required, or clang-tidy either ignores headers entirely or floods the output with findings from system and third-party headers.

`clang-analyzer-*` is absent from that `Checks:` list on purpose -- clang-tidy enables it by default and a config-file `Checks:` adds to the default set rather than replacing it, so the path-sensitive checks (use-after-free, uninitialized reads) run either way. Verify on the local toolchain with `clang-tidy --list-checks` if in doubt. What the list above *does* decide is `WarningsAsErrors`: `bugprone-*,cert-*` are fatal and analyzer findings are not, so a use-after-free warns and CI still goes green. Promoting `clang-analyzer-*` to fatal is defensible on a clean tree and hostile on a legacy one, since path-sensitive analysis has a real false-positive rate -- decide it deliberately and write the decision down, rather than inheriting the warn-only behavior by omission.

Run on a diff rather than the tree: `git diff -U0 origin/main | clang-tidy-diff.py -p1 -path build/dev`. Enabling the full check set on a legacy tree produces thousands of findings and gets the tool switched off.

`.clang-format` is the repo's, not a personal preference. Enforce with `clang-format --dry-run --Werror` in CI, and format only the changed lines (`git-clang-format`) so a formatting sweep never hides a logic change in the same commit.

## Cross-platform, before the first Windows CI run

A codebase that has only ever built on Linux hits the same sequence on its first MSVC lane. None are deep; each costs a CI cycle.

- **`NOMINMAX` before any Windows header.** `windows.h` defines `min` and `max` as macros, which breaks every `std::min`/`std::max` call and produces baffling errors inside templated headers (`error C2589: '(': illegal token on right side of '::'`). Set it project-wide as a compile definition, not per-file.
- **`/bigobj` on heavily templated code.** A deep template hierarchy generates enough sections per translation unit to exceed MSVC's default object-section limit on debug builds. Cheaper to add up front than to diagnose later.
- **POSIX functions MSVC does not have.** `timegm` is the common one; Microsoft's documented equivalent is `_mkgmtime` with identical semantics. Never substitute `mktime` as a fallback: it interprets the `tm` as **local** time and silently shifts every result by the runner's timezone offset, which produces wrong timestamps rather than a build error.
- **Object-handler and callback function pointers.** MSVC warns on incompatible function-pointer assignment (C4133) where GCC is silent, so a signature mismatch that has always been latent surfaces only on the Windows lane.

Run the widest warning set on the platform that is *not* used for daily development. Each compiler is silent about a different class, so a second toolchain in CI is a second static analyser for free.

## Build speed

- `ccache` (or `sccache`), wired in with `set(CMAKE_CXX_COMPILER_LAUNCHER ccache)`.
- Ninja over Make.
- `include-what-you-use` to cut transitive-include creep; a header that pulls in half the standard library slows every consumer.
- Precompiled headers (`target_precompile_headers`) for genuinely stable, widely-included sets only. On a churning header they make builds slower.
- Unity builds (`CMAKE_UNITY_BUILD`) can halve a full build and will break on anonymous-namespace and macro collisions. Verify the non-unity build still works in CI.

## Verify

- Configure and build clean from an empty build directory
- No directory-scoped `include_directories`/`add_definitions`/`CMAKE_CXX_FLAGS` appends in new CMake
- Every dependency consumed through a namespaced imported target
- `ctest --output-on-failure` passes, and individual cases are selectable by name
- ASan/UBSan preset builds and passes
- `clang-format --dry-run --Werror` produces no diff
