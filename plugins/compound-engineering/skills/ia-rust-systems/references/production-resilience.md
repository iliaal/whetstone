# Production Resilience

Load this reference when productionizing a Rust service — adding config validation, health endpoints, graceful shutdown, retry/timeout discipline, or connection pools. Not needed for CLI tools or dev-only code.

- **Fail-fast config**: parse and validate all config at startup with `serde` + a `Config::load() -> Result<Self>` that returns errors for missing/invalid values. Crash before binding the listen port, not on the first request.
- **Health endpoints**: `/health` (shallow liveness, returns 200 if the process responds) and `/ready` (deep readiness, verifies DB, cache, and downstream services). Load balancers route on `/ready`; orchestrators restart on `/health`. Diagnostic endpoints must redact secrets (tokens, passwords, API keys, PII) before returning.
- **Graceful shutdown**: install a `tokio::signal` handler, trigger a `CancellationToken`, drain in-flight requests with a timeout, then exit. Axum: `.with_graceful_shutdown(shutdown_signal)`.
- **Retries**: use `backon` or `tokio-retry` with exponential backoff + jitter. Retry only transient errors (connection reset, 429, 502/503/504). Never retry 4xx.
- **Timeouts on every network call** — no defaults. `tokio::time::timeout(dur, fut)` or `reqwest::Client::builder().timeout(dur)`.
- **Connection pools**: `sqlx::PgPool`, `reqwest::Client` — build once, clone (cheap, `Arc` inside), share via `State`.
