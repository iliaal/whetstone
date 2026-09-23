# Applications and testing

## CLI Tools (clap)

- Use the derive API: `#[derive(Parser)]` + `#[derive(Subcommand)]`. Less boilerplate, types drive the help text.
- One `enum Commands` variant per subcommand; flatten shared flags into a `#[command(flatten)] struct CommonArgs`.
- `--json` flag on query commands for agent/pipe consumption. Emit via `serde_json::to_string(&value)?`.
- Exit codes: 0 success, 1 for errors `main` returned, 2 for argparse (clap handles this), reserve 3+ for domain meanings documented in `--help`.
- Provide `--version` automatically via `#[command(version)]`.

See [cli-tools.md](./cli-tools.md) for config layering, logging setup, progress reporting, and shell completions.


## HTTP Services (axum)

- Framework default: **axum** (tokio-native, tower middleware, extractor-based handlers). Pick `actix-web` only if an existing codebase uses it.
- Handlers return `Result<impl IntoResponse, AppError>`. Implement `IntoResponse` for `AppError` to centralize error → status mapping.
- Validate input at the boundary: `axum::extract::Json<T>` where `T: Deserialize + Validate` (use `validator` crate). Internal services trust input was validated.
- Share state via `State<Arc<AppState>>`, not globals, not `lazy_static`.
- Middleware via `tower::ServiceBuilder`: tracing → timeout → auth → CORS → handler. Order matters.
- **Resilience layers** (outbound clients, shared services): combine `LoadShed` + `ConcurrencyLimit` for backpressure, not unbounded queueing; full tower stack in [production-resilience.md](./production-resilience.md).

See [axum-service.md](./axum-service.md) for project layout, extractors, error types, graceful shutdown, and OpenAPI generation.


## Testing

- Built-in `#[test]`. Prefer `cargo nextest run --workspace` over `cargo test`; it runs tests in parallel processes with proper isolation.
- Unit tests live in `mod tests { ... }` at the bottom of the file (access to private items).
- Integration tests in `tests/` directory. One file per public surface area.
- `#[tokio::test]` for async tests. Add `flavor = "multi_thread"` when the code under test spawns tasks.
- `rstest` for parametrized tests and fixtures. `proptest` / `quickcheck` for property-based tests on pure logic.
- `insta` for snapshot testing CLI output, serialization, large structs. Review diffs with `cargo insta review`.
- `assert_cmd` + `predicates` for CLI integration tests (invokes the binary, asserts on stdout/stderr/exit code).
- **Assert on error variants with `matches!`**: `assert!(matches!(result.unwrap_err(), MyError::Validation(_)))`. No `match` arms to update when unrelated variants are added.
- Coverage: `cargo llvm-cov --workspace --html`. Target 70%+ on application code, higher on library crates.
- **Fuzzing for parsers**: `cargo fuzz` + `libfuzzer-sys` on any code parsing untrusted input; nightly runs surface panics and UB unit tests miss.
- **Never mutate process-global state in a test.** `set_var("TMPDIR", …)` in one test makes every *concurrent* `tempfile::tempdir()` create its scratch dir inside that test's `TempDir`, which is recursively deleted when it drops. The smoking gun is nested temp paths (`/tmp/.tmpXXXX/.tmpYYYY/…`) and `ENOENT` on files a victim just created, with the failing test rotating between runs. A mutex around the env-mutating tests does not fix it: the victims never take the mutex. Refactor the function under test into a thin env-reading wrapper over an env-free core that takes the values as parameters, and test the core.
- **A concurrent `Command::spawn` briefly extends the lifetime of every open file descriptor.** `fork` duplicates the whole parent fd table and only `exec`'s `CLOEXEC` closes the copies, so in that window a sibling test holds the caller's lock fd or its just-written script's write fd. Two symptoms, one cause: an `flock` that outlives its guard's `drop` (a test asserting "drop released it, re-acquire succeeds immediately" fails roughly 1 run in 12 next to spawn-heavy tests, 0 in N alone; fix with a bounded poll-acquire to a deadline, not a one-shot assert) and `ErrorKind::ExecutableFileBusy` on exec'ing a file just `chmod +x`'d (fix with a bounded retry around the spawn). The already-held assertion needs no change in either case.

For generic test discipline (anti-patterns, mock rules, rationalization resistance), see the `ia-writing-tests` skill.


## Production Resilience

When productionizing a service (config validation, `/health` + `/ready` endpoints, graceful shutdown, retries/timeouts/jitter, deny-by-default fallback when the call is the security decision, connection pools, diagnostic secret redaction), load [production-resilience.md](./production-resilience.md).


## Observability

For logging (`tracing` + `tracing-subscriber` with init recipe), `#[instrument]` spans, correlation IDs, metrics, and distributed tracing patterns, load [observability.md](./observability.md). Never use `println!` or `log::` in new code.
