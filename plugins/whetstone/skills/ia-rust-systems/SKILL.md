---
name: ia-rust-systems
class: language
description: >-
  Rust patterns for CLI tools, backend services, and general application code.
  Use when working with Rust, Cargo workspaces, axum/tokio services, clap CLIs,
  async concurrency, or configuring clippy, rustfmt, cargo-nextest, or Cargo.toml.
paths: "**/*.rs,**/Cargo.toml"
---

# Rust Systems & Services

Covers modern application-layer Rust (edition 2024): CLIs, web services, libraries. Not `no_std`/embedded.

## Working rules

- Preserve error variants in libraries and add operational context at application boundaries.
- Distinguish missing configuration from unreadable or invalid files before writing replacements.
- Keep blocking work off async workers, bound queues and spawned work, and define shutdown behavior.
- Trace exported interfaces before treating a change as internal; verify installed runtime capabilities.
- Do not mutate process-wide state in concurrent tests; exercise the real binary and relevant feature combinations.

## Unsafe Discipline

- Default: no `unsafe`. If clippy flags it, don't `#[allow]` it; refactor. The `#[expect]` escape hatch below does not apply here; unsafe findings get fixed, not annotated.
- Every `unsafe` block gets a `// SAFETY:` comment above it explaining why each invariant holds. No comment = reviewer rejects.
- Keep `unsafe` blocks minimal: wrap in a safe abstraction at module boundary, mark the module `pub(crate)`.
- Use `miri` (`cargo +nightly miri test`) on any crate containing `unsafe` or raw pointer arithmetic; it catches UB that optimizers mask.
- Prefer `bytemuck`, `zerocopy`, `bytes` over hand-rolled transmutes for zero-copy patterns.
- **Env-var writes are `unsafe` in edition 2024. Write them only in `main`, before the runtime starts or any thread spawns.** Concurrent `getenv` is UB; `OnceLock` does not make it safe. Watch for lazy `LD_LIBRARY_PATH`-style writes on first use; hoist them to startup.


## Discipline

- Simplicity first: every change as simple as possible, impact minimal code.
- Only touch what's necessary; avoid unrelated changes in a PR.
- No `#[allow(clippy::...)]` as a shortcut; fix the underlying issue. When a suppression is genuinely warranted, write `#[expect(clippy::lint_name, reason = "...")]` instead: `expect` warns once the lint stops firing, so a suppression that has outlived its cause reports itself, where `allow` rots silently forever. (`expect` needs Rust 1.81+; edition 2024 clears that floor.)
- Before adding a trait or generic, verify it's used in 3+ places. Otherwise a concrete type is clearer.
- **`bool::then_some(x)` takes `x` by value: the argument is computed before the bool is consulted**, so a guard written as a condition plus a fixed-width slice panics on exactly the inputs the condition was checking for: `(b.len() >= 19 && b[4] == b'-').then_some(&v[..19])` panics on any shorter value, exiting 101 inside the one function written to report the case as undetermined. Use `then(|| …)`, which is lazy. Clippy does not flag the difference. Grep `then_some(` for an argument that indexes, slices, unwraps, or allocates. Related: **a fixed-width slice is not a parse**. `&v[..19]` also panics mid-character on non-ASCII, and comparing two such prefixes lexicographically drops the timezone offset, so `01:00+02:00` sorts after `00:00Z` while being an hour earlier. Parse and normalize, or reject.


## Verify

- `cargo fmt --all -- --check` passes with zero diffs
- `cargo clippy --workspace --all-targets --all-features -- -D warnings` passes
- `cargo nextest run --workspace` (or `cargo test --workspace`) passes with zero failures
- `cargo deny check` passes (licenses, advisories, duplicates) for any crate going to production
- No new `unsafe` without `// SAFETY:` comment

## Task-specific references

Read the relevant reference before implementing or reviewing the matching behavior:

- For Cargo setup, workspace changes, public API reachability, build profiles, or CI: [toolchain-and-interfaces.md](./references/toolchain-and-interfaces.md).
- For errors, ownership, parsing boundaries, Tokio, shutdown, or concurrency: [ownership-and-execution.md](./references/ownership-and-execution.md).
- For CLI/service entrypoints, production resilience, telemetry, or tests: [applications-and-testing.md](./references/applications-and-testing.md).

Existing specialized references, when the corresponding topic applies:

- [macros-and-os-boundaries.md](./references/macros-and-os-boundaries.md).
- [rustdoc.md](./references/rustdoc.md).
- [build-profiles.md](./references/build-profiles.md).
- [performance.md](./references/performance.md).
- [cli-tools.md](./references/cli-tools.md).
- [production-resilience.md](./references/production-resilience.md).
- [axum-service.md](./references/axum-service.md).
- [observability.md](./references/observability.md).
- [ci-pipeline.md](./references/ci-pipeline.md).
