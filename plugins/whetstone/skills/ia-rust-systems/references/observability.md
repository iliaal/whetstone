# Observability for Rust Services

Load this reference when adding logging, tracing, metrics, or distributed tracing to a Rust service. `println!` and `log::` are forbidden in new code; use `tracing` + `tracing-subscriber`.

## Logging

- `tracing` + `tracing-subscriber` with `json()` formatter in production, `fmt().pretty()` in dev.
- **Init recipe**: build subscriber layers and register once at `main` entry. Respect `RUST_LOG` for runtime filter override, include thread IDs for concurrent contexts, gate OpenTelemetry behind a feature flag so dev builds don't pull the whole OTEL SDK:

  ```rust
  pub fn init_tracing() {
      let fmt_layer = tracing_subscriber::fmt::layer()
          .with_target(false)
          .with_thread_ids(true);
      let filter_layer = tracing_subscriber::EnvFilter::try_from_default_env()
          .unwrap_or_else(|_| "info".into());
      tracing_subscriber::registry()
          .with(filter_layer)
          .with(fmt_layer)
          .init();
  }
  ```

## Structured Spans

- `#[tracing::instrument(skip(large_arg), fields(user_id = %user.id))]` on service methods: automatic span creation, structured fields.
- Skip large args to keep spans lightweight; prefer named fields over stringified args.

## Correlation IDs

Extract or generate at ingress middleware, attach to the root span, propagate via `traceparent` header to downstream calls. Required for any multi-service system.

## Metrics

`metrics` crate with `metrics-exporter-prometheus`. Counter for traffic/errors, Histogram for latency, Gauge for saturation. Label cardinality bounded: no user IDs, no unbounded dimensions.

## Distributed Tracing

`tracing-opentelemetry` exports spans to Jaeger/Tempo/Honeycomb/Datadog. Gate the OpenTelemetry subscriber behind a feature flag to keep dev/test builds fast.

## Live Task Introspection (tokio-console)

Distinct from log/metric/trace export: `tokio-console` attaches to a running process and shows every Tokio task's state, poll count, busy/scheduled/idle durations with a poll-time histogram, and wakeup counts, and warns on self-wakes, lost wakers, and tasks that never yield. It is the tool for a stuck or spinning task that emits no log line. Add the `console-subscriber` crate as a `tracing-subscriber` layer (`console_subscriber::init()` or `ConsoleLayer::builder()` alongside the fmt layer) and build with `RUSTFLAGS="--cfg tokio_unstable"` (or `rustflags = ["--cfg", "tokio_unstable"]` in `.cargo/config.toml`); without that cfg Tokio emits no task instrumentation. Keep it behind a feature flag like the OTel layer: it is a debugging aid, not production telemetry.
