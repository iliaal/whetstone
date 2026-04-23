# Observability for Rust Services

Load this reference when adding logging, tracing, metrics, or distributed tracing to a Rust service. `println!` and `log::` are forbidden in new code — use `tracing` + `tracing-subscriber`.

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

- `#[tracing::instrument(skip(large_arg), fields(user_id = %user.id))]` on service methods — automatic span creation, structured fields.
- Skip large args to keep spans lightweight; prefer named fields over stringified args.

## Correlation IDs

Extract or generate at ingress middleware, attach to the root span, propagate via `traceparent` header to downstream calls. Required for any multi-service system.

## Metrics

`metrics` crate with `metrics-exporter-prometheus`. Counter for traffic/errors, Histogram for latency, Gauge for saturation. Label cardinality bounded — no user IDs, no unbounded dimensions.

## Distributed Tracing

`tracing-opentelemetry` exports spans to Jaeger/Tempo/Honeycomb/Datadog. Gate the OpenTelemetry subscriber behind a feature flag to keep dev/test builds fast.
