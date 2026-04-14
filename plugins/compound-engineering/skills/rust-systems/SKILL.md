---
name: rust-systems
description: >-
  Rust patterns for CLI tools, backend services, and general application code.
  Use when working with Rust, Cargo workspaces, axum/tokio services, clap CLIs,
  async concurrency, or configuring clippy, rustfmt, cargo-nextest, or Cargo.toml.
paths: "**/*.rs,**/Cargo.toml"
---

# Rust Systems & Services

Covers modern application-layer Rust (edition 2024): CLIs, web services, libraries. Not `no_std`/embedded.

## Tooling

| Tool | Purpose |
|------|---------|
| `cargo` | Build, dep management, script runner |
| `clippy` | Lint (`cargo clippy --workspace --all-targets -- -D warnings`) |
| `rustfmt` | Formatter (`cargo fmt --all`) |
| `cargo-nextest` | Test runner, 2-3x faster than `cargo test`, better isolation |
| `cargo-deny` | License + advisory + duplicate-dep checks |
| `cargo-machete` | Find unused dependencies |

- Pin `rust-toolchain.toml` per repo so every contributor and CI uses the same compiler.
- `cargo update -p <crate>` for single-package upgrades. `cargo update` rewrites everything — avoid in PR diffs.
- `Cargo.lock` goes in version control for binaries *and* libraries (modern guidance; reproducibility wins).

## Workspaces

Multi-crate projects use a workspace with layered crates. Dependencies point inward only.

```
Cargo.toml                  # [workspace] members + [workspace.dependencies]
crates/
  protocol/    # Shared types, no deps on other workspace crates
  storage/     # Persistence, depends on protocol
  service/    # Business logic, depends on protocol + storage
  cli/        # Binary, depends on everything
```

- Centralize versions in `[workspace.dependencies]`, reference as `foo = { workspace = true }` in members.
- Keep the leaf-most crate (`protocol` / types) dependency-free so every other crate can depend on it without cycles.
- Feature flags belong on the crate that introduces the dependency, not re-exported through the workspace root.
- **Library crates expose one stable facade**: a thin `lib.rs` with a `//!` module doc comment stating purpose, followed by `pub use` re-exports of the public surface. Consumers learn one import path per concept; internal module layout can be reorganized without breaking callers.
- **Feature gates must error, never silently degrade.** If runtime config requests a capability the binary wasn't compiled with (e.g. `device = "gpu"` on a non-CUDA build), fail at startup with a clear error. Silent fallback produces different behavior from what the operator configured, often without anyone noticing.

## Error Handling

Split by crate role:

- **Libraries / lower crates**: define typed errors with `thiserror`. Consumers can pattern-match.
- **Binaries / top-level crates**: use `anyhow::Result` with `.context("what was being attempted")`. Human-readable error chains.
- Never return `Box<dyn Error>` from library APIs — it erases variant information.
- Use `?` liberally. Never `.unwrap()` or `.expect()` outside tests and `main`. An `expect("...")` is acceptable only when the invariant is provably upheld and the message explains why.
- Convert at boundaries: `#[from]` on thiserror variants for auto-conversion; `.map_err(MyError::from)` when explicit.
- `bail!("...")` / `ensure!(cond, "...")` in application code for early exits.
- Prefer `Result<T, E>` over panics for any recoverable error. Panics are for programmer bugs (broken invariants), not runtime failures.
- **`#[must_use]` on fallible APIs**: annotate functions returning `Result` or newtype-wrapped results that callers frequently ignore. Catches `let _ = validate(x);` at compile time instead of shipping a silently-dropped error.

## Ownership Discipline

- Take `&str` over `&String`, `&[T]` over `&Vec<T>` in function signatures — accepts more call sites for free.
- Return owned (`String`, `Vec<T>`) from constructors and public APIs. Borrow in hot paths where lifetimes are obvious.
- Reach for `Arc<T>` only when sharing across threads. Single-threaded sharing uses `Rc<T>` or references.
- `Cow<'_, str>` when a function sometimes allocates and sometimes borrows (e.g. normalization).
- Lifetime elision handles 90% of cases. If you're writing `'a` in more than one signature, reconsider whether that type should own its data instead.

## Async with Tokio

- Default runtime: `#[tokio::main]` with `features = ["full"]` for apps; `features = ["rt", "macros", "sync"]` for libraries that need to stay slim.
- `tokio::spawn` for independent tasks. `JoinSet` for a dynamic group you'll await together with cancellation.
- `tokio::select!` for racing futures (timeouts, cancellation, first-wins).
- Never block the runtime: `tokio::task::spawn_blocking` for sync CPU work or blocking I/O libs.
- `tokio::sync::Mutex` only when the guard must be held across `.await`. Otherwise `std::sync::Mutex` is faster.
- **`tokio::sync::RwLock` when reads dominate writes** (config snapshots, route tables, hot caches). Many readers proceed in parallel; `Mutex` serializes them. For snapshot-swap semantics (rarely-updated config), `arc-swap::ArcSwap` is faster still — no lock on the read path.
- Cancellation: `CancellationToken` (from `tokio-util`) propagates shutdown. Long-running tasks must check it.
- Backpressure via bounded `mpsc` channels — unbounded channels hide memory growth until OOM.
- **`Semaphore` for hard concurrency limits** on spawn paths that don't fit a channel model (e.g. "at most 50 concurrent outbound HTTP calls"). `let _permit = sem.acquire().await?;` inside the task; dropping the permit releases the slot. Pair with `Arc<Semaphore>` shared across spawners.
- Don't mix async runtimes. Pick `tokio` and stick with it; `async-std` and `smol` don't interop cleanly.

## CLI Tools (clap)

- Use the derive API: `#[derive(Parser)]` + `#[derive(Subcommand)]`. Less boilerplate, types drive the help text.
- One `enum Commands` variant per subcommand; flatten shared flags into a `#[command(flatten)] struct CommonArgs`.
- `--json` flag on query commands for agent/pipe consumption. Emit via `serde_json::to_string(&value)?`.
- Exit codes: 0 success, 1 for errors `main` returned, 2 for argparse (clap handles this), reserve 3+ for domain meanings documented in `--help`.
- Provide `--version` automatically via `#[command(version)]`.

See [cli-tools.md](./references/cli-tools.md) for config layering, logging setup, progress reporting, and shell completions.

## HTTP Services (axum)

- Framework default: **axum** (tokio-native, tower middleware, extractor-based handlers). Pick `actix-web` only if an existing codebase uses it.
- Handlers return `Result<impl IntoResponse, AppError>`. Implement `IntoResponse` for `AppError` to centralize error → status mapping.
- Validate input at the boundary: `axum::extract::Json<T>` where `T: Deserialize + Validate` (use `validator` crate). Internal services trust input was validated.
- Share state via `State<Arc<AppState>>` — not globals, not `lazy_static`.
- Middleware via `tower::ServiceBuilder`: tracing → timeout → auth → CORS → handler. Order matters.

See [axum-service.md](./references/axum-service.md) for project layout, extractors, error types, graceful shutdown, and OpenAPI generation.

## Concurrency

| Workload | Approach |
|----------|----------|
| Independent async I/O | `tokio::spawn` + `JoinSet` or `futures::join!` |
| Data-parallel CPU work | `rayon` with `par_iter` |
| Shared mutable state across threads | `Arc<Mutex<T>>` or `Arc<RwLock<T>>`, smallest scope possible |
| Single-producer pipelines | `tokio::sync::mpsc` (async) or `std::sync::mpsc` (sync) |
| Broadcast / fan-out | `tokio::sync::broadcast` |

`rayon` and `tokio` coexist — use `tokio::task::spawn_blocking` to call a rayon pool from async code. Never call `.block_on()` from inside a tokio task; it deadlocks the runtime.

## Testing

- Built-in `#[test]`. Prefer `cargo nextest run --workspace` over `cargo test` — it runs tests in parallel processes with proper isolation.
- Unit tests live in `mod tests { ... }` at the bottom of the file (access to private items).
- Integration tests in `tests/` directory. One file per public surface area.
- `#[tokio::test]` for async tests. Add `flavor = "multi_thread"` when the code under test spawns tasks.
- `rstest` for parametrized tests and fixtures. `proptest` / `quickcheck` for property-based tests on pure logic.
- `insta` for snapshot testing CLI output, serialization, large structs. Review diffs with `cargo insta review`.
- `assert_cmd` + `predicates` for CLI integration tests (invokes the binary, asserts on stdout/stderr/exit code).
- **Assert on error variants with `matches!`**: `assert!(matches!(result.unwrap_err(), MyError::Validation(_)))`. Cleaner than `match` arms when the test only cares whether the error is the right kind, and doesn't force updates when unrelated variants are added.
- Coverage: `cargo llvm-cov --workspace --html`. Target 70%+ on application code, higher on library crates.

For generic test discipline (anti-patterns, mock rules, rationalization resistance), see the `writing-tests` skill.

## Unsafe Discipline

- Default: no `unsafe`. If clippy flags it, don't `#[allow]` it — refactor.
- Every `unsafe` block gets a `// SAFETY:` comment above it explaining why each invariant holds. No comment = reviewer rejects.
- Keep `unsafe` blocks minimal — wrap in a safe abstraction at module boundary, mark the module `pub(crate)`.
- Use `miri` (`cargo +nightly miri test`) on any crate containing `unsafe` or raw pointer arithmetic — catches UB that optimizers mask.
- Prefer `bytemuck`, `zerocopy`, `bytes` over hand-rolled transmutes for zero-copy patterns.

## Production Resilience

- **Fail-fast config**: parse and validate all config at startup with `serde` + a `Config::load() -> Result<Self>` that returns errors for missing/invalid values. Crash before binding the listen port, not on the first request.
- **Health endpoints**: `/health` (shallow liveness, returns 200 if the process responds) and `/ready` (deep readiness, verifies DB, cache, and downstream services). Load balancers route on `/ready`; orchestrators restart on `/health`.
- **Graceful shutdown**: install a `tokio::signal` handler, trigger a `CancellationToken`, drain in-flight requests with a timeout, then exit. Axum: `.with_graceful_shutdown(shutdown_signal)`.
- **Retries**: use `backon` or `tokio-retry` with exponential backoff + jitter. Retry only transient errors (connection reset, 429, 502/503/504). Never retry 4xx.
- **Timeouts on every network call** — no defaults. `tokio::time::timeout(dur, fut)` or `reqwest::Client::builder().timeout(dur)`.
- **Connection pools**: `sqlx::PgPool`, `reqwest::Client` — build once, clone (cheap, `Arc` inside), share via `State`.

## Observability

- **Logging**: `tracing` + `tracing-subscriber` with `json()` formatter in production, `fmt().pretty()` in dev. Never `println!` or `log::` in new code.
- `#[tracing::instrument(skip(large_arg), fields(user_id = %user.id))]` on service methods — automatic span creation, structured fields.
- **Correlation IDs**: extract/generate at ingress middleware, attach to the root span, propagate via `traceparent` header to downstream calls.
- **Metrics**: `metrics` crate with `metrics-exporter-prometheus`. Counter for traffic/errors, Histogram for latency, Gauge for saturation. Label cardinality bounded — no user IDs.
- **Distributed tracing**: `tracing-opentelemetry` exports spans to Jaeger/Tempo/etc.

## Discipline

- Simplicity first — every change as simple as possible, impact minimal code.
- Only touch what's necessary — avoid unrelated changes in a PR.
- No `#[allow(clippy::...)]` as a shortcut — fix the underlying issue. Document exceptions with a rationale.
- Before adding a trait or generic, verify it's used in 3+ places. Otherwise a concrete type is clearer.
- Verify: see Verify section — pass all checks with zero warnings before declaring done.

## Verify

- `cargo fmt --all -- --check` passes with zero diffs
- `cargo clippy --workspace --all-targets --all-features -- -D warnings` passes
- `cargo nextest run --workspace` (or `cargo test --workspace`) passes with zero failures
- `cargo deny check` passes (licenses, advisories, duplicates) for any crate going to production
- No new `unsafe` without `// SAFETY:` comment

## References

- [cli-tools.md](./references/cli-tools.md) — clap patterns, config layering, tracing setup, progress, shell completions
- [axum-service.md](./references/axum-service.md) — project layout, extractors, error types, graceful shutdown, testing
