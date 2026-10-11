# Observability for Rust Services

Load this reference when adding logging, tracing, metrics, or distributed tracing to a Rust service. `println!` and `log::` are forbidden in new code; use `tracing` + `tracing-subscriber`.

## Logging

- `tracing` + `tracing-subscriber` with `json()` formatter in production, `fmt().pretty()` in dev.
- **Init recipe**: build subscriber layers and register once at `main` entry. Respect `RUST_LOG` for runtime filter override, include thread IDs for concurrent contexts, gate OpenTelemetry behind a feature flag so dev builds don't pull the whole OTEL SDK:

  ```rust
  use tracing_subscriber::prelude::*;

  pub fn init_tracing() {
      let fmt_layer = tracing_subscriber::fmt::layer()
          .with_target(false)
          .with_thread_ids(true);
      let filter_layer = tracing_subscriber::EnvFilter::try_from_default_env()
          .unwrap_or_else(|_| "info".into());
      tracing_subscriber::registry()
          .with(fmt_layer.with_filter(filter_layer))
          .init();
  }
  ```

## Structured Spans

- Use `#[tracing::instrument(skip_all, fields(user_id = %user.id))]` on service methods for automatic span creation with explicitly selected safe fields.
- Skip all arguments by default to avoid capturing credentials or large values; record only safe named fields.
- Never hold a `Span::enter()` guard across `.await`; use `#[instrument(skip_all)]` with explicitly selected safe fields or `.instrument(span)` so other tasks do not inherit the entered span.

## Correlation IDs

Extract or generate at ingress middleware, attach to the root span, propagate via `traceparent` header to downstream calls. Required for any multi-service system.

## Metrics

`metrics` crate with `metrics-exporter-prometheus`. Counter for traffic/errors, Histogram for latency, Gauge for saturation. Label cardinality bounded: no user IDs, no unbounded dimensions.

## Distributed Tracing

`tracing-opentelemetry` exports spans to Jaeger/Tempo/Honeycomb/Datadog. Gate the OpenTelemetry subscriber behind a feature flag to keep dev/test builds fast.

## Live Task Introspection (tokio-console)

Distinct from log/metric/trace export: `tokio-console` attaches to a running process and shows every Tokio task's state, poll count, busy/scheduled/idle durations with a poll-time histogram, and wakeup counts, and warns on self-wakes, lost wakers, and tasks that never yield. It is the tool for a stuck or spinning task that emits no log line. Add `.with(console_subscriber::spawn())` to the registry chain before the single `.init()` call. Keep the log filter on the fmt layer as above so it does not suppress console instrumentation. Use `console_subscriber::init()` only as a standalone replacement for the initialization recipe; it installs the global subscriber itself. Build with `RUSTFLAGS="--cfg tokio_unstable"` (or `rustflags = ["--cfg", "tokio_unstable"]` in `.cargo/config.toml`); without that cfg Tokio emits no task instrumentation. Keep it behind a feature flag like the OTel layer: it is a debugging aid, not production telemetry.
