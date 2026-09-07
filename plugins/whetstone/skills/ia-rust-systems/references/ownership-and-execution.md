# Ownership and execution

## Error Handling

Split by crate role:

- **Libraries / lower crates**: define typed errors with `thiserror`. Consumers can pattern-match.
- **Binaries / top-level crates**: use `anyhow::Result` with `.context("what was being attempted")`. Human-readable error chains.
- Never return `Box<dyn Error>` from library APIs — it erases variant information.
- Use `?` liberally. Never `.unwrap()` or `.expect()` outside tests and `main`. An `expect("...")` is acceptable only when the invariant is provably upheld and the message explains why.
- Convert at boundaries: `#[from]` on thiserror variants for auto-conversion; `.map_err(MyError::from)` when explicit.
- `bail!("...")` / `ensure!(cond, "...")` in application code for early exits.
- Prefer `Result<T, E>` over panics for any recoverable error. Panics are for programmer bugs (broken invariants), not runtime failures.
- **`#[must_use]` on fallible APIs**: `Result` already warns on implicit unused results; annotate custom result wrappers or functions to add a specific diagnostic. Deny `unused_must_use` when that warning must fail the build. Explicit discard (`let _ = validate(x);`) bypasses the lint even when denied, so review intentional discards separately.
- **Make illegal call-sequences unrepresentable** — the type-state pattern: encode a mandatory call order as distinct types (`Client<Uninitialized>` → `Client<Connected>`) so an out-of-order call fails to compile instead of erroring at runtime.
- **`fs::read_to_string(p).unwrap_or_default()` to mean "an absent file is an empty config" swallows every read error, not just `NotFound`.** A file that exists but cannot be read — permission denied, invalid UTF-8, transient I/O — collapses to empty, and the next step writes a fresh file over the comments and unrelated entries the read never surfaced. Match the kind: `Err(e) if e.kind() == ErrorKind::NotFound => Ok(default)`, everything else propagates with context. Test it by writing invalid UTF-8 bytes to the path and asserting the operation returns `Err` *and* leaves the bytes untouched.


## Ownership Discipline

- Take `&str` over `&String`, `&[T]` over `&Vec<T>` in function signatures — accepts more call sites for free.
- Return owned (`String`, `Vec<T>`) from constructors and public APIs. Borrow in hot paths where lifetimes are obvious.
- Reach for `Arc<T>` only when sharing across threads. Single-threaded sharing uses `Rc<T>` or references.
- `Cow<'_, str>` when a function sometimes allocates and sometimes borrows (e.g. normalization).
- Rely on lifetime elision. More than one signature needing an explicit `'a` is a signal the type should own its data — convert the borrow to owned before adding lifetimes.
- Reducing hot-path allocations (SmallVec, ArrayVec, string interning, `Bytes`, vectored writes): profile first, then load [performance.md](./performance.md).
- **`str::lines()` splits on `\n` only.** A line-oriented scanner ported from a language with universal newlines (Python, Ruby) silently merges a bare-`\r` file into one line — in a redaction or filtering tool that is a security divergence, not a formatting one: the whole body rides through on whatever classification the merged first line matched. Write the splitter explicitly over CR, LF and CRLF, and emit the **original bytes** for every line the rules did not change rather than re-encoding a decoded copy — a round-trip through lossy decoding transcodes lines the tool was supposed to pass through untouched.
- **The `regex` crate has no look-around.** If a rule is defined by a lookbehind or lookahead, reach for `fancy-regex` rather than hand-rolling boundary checks, which drift from the reference on the one input nobody tried. Three neighbours that type-check and still diverge: `regex::bytes` still applies Unicode `\b` (a byte-oriented token scan wants `(?-u:\b)`, or `cafémb-x1z` passes a boundary check ASCII `\b` would have failed); `str::to_lowercase()` is not case folding (`ß` maps to `ss` only under casefold, so a hash key derived from case-folded text differs between implementations — use `caseless`); and `char::is_whitespace()` excludes U+001C–U+001F, which Python's `\s` and `str.strip()` include.


## Async with Tokio

- Default runtime: `#[tokio::main]` with `features = ["full"]` for apps; `features = ["rt", "macros", "sync"]` for libraries that need to stay slim.
- `tokio::spawn` for independent tasks. `JoinSet` for a dynamic group awaited together with cancellation.
- `tokio::select!` for racing futures (timeouts, cancellation, first-wins).
- Never block the runtime: `tokio::task::spawn_blocking` for sync CPU work or blocking I/O libs.
- `tokio::sync::Mutex` only when the guard must be held across `.await`. Otherwise `std::sync::Mutex` is faster.
- **`tokio::sync::RwLock` when reads dominate writes** (config snapshots, route tables, hot caches). Many readers proceed in parallel; `Mutex` serializes them. For snapshot-swap semantics (rarely-updated config), `arc-swap::ArcSwap` is faster still — no lock on the read path.
- Cancellation: `CancellationToken` (from `tokio-util`) propagates shutdown. Long-running tasks must check it.
- Backpressure via bounded `mpsc` channels — unbounded channels hide memory growth until OOM.
- **`Semaphore` for hard concurrency limits** on spawn paths that don't fit a channel model (e.g. "at most 50 concurrent outbound HTTP calls"). `let _permit = sem.acquire().await?;` inside the task; dropping the permit releases the slot. Pair with `Arc<Semaphore>` shared across spawners.
- Don't mix async runtimes. Pick `tokio` and stick with it; `async-std` and `smol` don't interop cleanly.
- **A manually-constructed `Runtime`'s `Drop` joins already-running `spawn_blocking` tasks.** A daemon whose shutdown must not wait on wedged blocking work (long inference, stuck I/O) has to finish its cleanup and `std::process::exit(0)` rather than let the runtime drop, or use `shutdown_timeout`. `JoinSet::abort_all` does not help — abort takes effect at an await point, and a blocking closure that has already started has none.
- **`std::process::exit` skips Rust `Drop` glue, not C++ static destructors.** It is an ordinary `exit(3)`, so every handler a native library registered through `__cxa_atexit` still runs — which is where a heap diagnostic from an FFI runtime's teardown fires, non-deterministically and under load. `libc::_exit(code)` walks no handler table at all. Reach for it only after proving nothing is left to run: flush stdio, drop owning values on the normal path, and confirm no atexit hook or tempfile destructor is being relied on.
- **A panic inside a spawned per-request task is worse than an error.** Without a `catch_unwind` the panic unwinds that one task: the connection survives, no response is ever sent for that request id, and the caller waits until its own timeout. So every reachable `unwrap`/`expect`/slice index in a handler — a DB row with an unexpected enum string, a model output of unexpected shape, an index derived from untrusted input — is a client hang rather than a crash anyone would notice. Running the handler body under `spawn_blocking` gives the boundary for free: a panic arrives as a `JoinError` you convert into an error response, and the same call offloads the blocking work.


## Concurrency

| Workload | Approach |
|----------|----------|
| Independent async I/O | `tokio::spawn` + `JoinSet` or `futures::join!` |
| Data-parallel CPU work | `rayon` with `par_iter` |
| Shared mutable state across threads | `Arc<Mutex<T>>` or `Arc<RwLock<T>>`, smallest scope possible |
| Single-producer pipelines | `tokio::sync::mpsc` (async) or `std::sync::mpsc` (sync) |
| Broadcast / fan-out | `tokio::sync::broadcast` |

`rayon` and `tokio` coexist — use `tokio::task::spawn_blocking` to call a rayon pool from async code. Never call `.block_on()` from inside a tokio task; it deadlocks the runtime.
