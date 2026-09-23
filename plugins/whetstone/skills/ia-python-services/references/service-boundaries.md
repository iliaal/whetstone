# Service boundaries

## Observability

- **Define "working" before instrumenting**: write the questions an on-call engineer will ask when this breaks ("which dependency is slow?", "is it all callers or one?"), then add only the telemetry that answers them. Instrumentation with no question behind it is cost and noise.
- **Pick the signal by the question it answers**: logs = "what happened in this one case?" (high-detail, sampled under load); metrics = "how often / how fast / how saturated?" (cheap aggregates, bounded cardinality); traces = "where did the time or error go across services?".
- **structlog** for JSON structured logging. Configure once at startup with `JSONRenderer`, `TimeStamper`, `merge_contextvars`
- **Correlation IDs**: generate at ingress (`X-Correlation-ID` header), bind to `contextvars`, propagate to downstream calls
- **Log levels**: DEBUG=diagnostics, INFO=operations, WARNING=anomalies handled, ERROR=failures needing attention. Never log expected behavior at ERROR
- **Prometheus metrics**: track latency (Histogram), traffic (Counter), errors (Counter), saturation (Gauge). Keep label cardinality bounded (no user IDs)
- **OpenTelemetry** for distributed tracing across services: start the SDK before importing the libraries it patches, or auto-instrumentation no-ops. Before trusting a signal, force an error and test traffic in staging and confirm the log/metric/trace lands; untested instrumentation fails silent
- **Alert on symptoms, not causes**: page on user-visible symptoms (error-rate spike, latency SLO burn, readiness flapping), not on causes (CPU high, queue depth growing). A cause with no symptom is a dashboard, not a page.
- **Never mutate `LogRecord` attributes from a `Formatter`.** A custom `logging.Formatter.format()` that rewrites `record.name` (or any record attribute) in place leaks to every other handler attached to the same logger and to pytest `caplog`. `Logger.callHandlers` passes the same `LogRecord` object to each handler; whichever formats first wins the mutation, and downstream handlers and test filters see the modified state. Tests filtering by full logger name (`if r.name == "src.services.foo"`) then silently miss; routing handlers doing `LOGGER_TO_MODEL.get(record.name)` fall through to defaults. Use a `logging.Filter` that adds a non-mutating attribute (`record.short_name`) and reference it in the format string as `%(short_name)s`, or override `formatMessage` instead of `format`. `try`/`finally` restore works for synchronous handler chains but is fragile under async handlers that interleave.


## Error Handling

- Validate inputs at boundaries before expensive ops. Report all errors at once when possible
- Use specific exceptions: `ValueError`, `TypeError`, `KeyError`, not bare `Exception`
- `raise ServiceError("upload failed") from e`: always chain to preserve debug trail
- Convert external data to domain types (enums, Pydantic models) at system boundaries
- Batch processing: `BatchResult(succeeded={}, failed={})`; don't let one item abort the batch
- Pydantic `BaseModel` with `field_validator` for complex input validation


## Migrations

- Separate schema and data migrations; data backfills in their own migration file
- Renames/removals use expand-contract: add new column → backfill → switch reads → drop old (see `ia-postgresql` skill for the full pattern)
- Never edit a migration that has already run in a shared environment
- Alembic: use `--autogenerate` as a starting point, always review generated SQL before committing
- Test migrations against production-sized data; a migration that takes 2ms on dev can lock a table for minutes in production


## API Design

- **Contract-first**: define Pydantic `BaseModel` request/response schemas and FastAPI `response_model` before writing endpoint logic. The schema is the contract; implementation follows. Generate OpenAPI docs from these models automatically.
- **Hyrum's Law awareness**: every observable response field, ordering, or timing becomes a dependency for callers. Use explicit `response_model` and `model_config = ConfigDict(extra="forbid")` to control exactly what's serialized; never return raw dicts or ORM objects from endpoints.
- **Addition over modification**: add new optional fields (`field: str | None = None`) rather than changing or removing existing ones. Removing a Pydantic field from a response model breaks callers silently. Deprecate first (`Field(deprecated=True)`), remove in a later version.
- **Consistent error structure**: all exceptions should produce the same envelope: `{"error": {"code": "...", "message": "...", "details": ...}}`. Register `@app.exception_handler` for `RequestValidationError`, `HTTPException`, and application-specific exceptions to normalize into one format. Callers build error handling once.
- **Boundary validation via Pydantic**: validate at the endpoint/handler level with Pydantic models and FastAPI's automatic request parsing. Internal services and repositories trust that input was validated at entry, with no redundant validation scattered through business logic.
- **Third-party responses are untrusted data**: validate shape and content of external API responses before using them in logic, rendering, or decision-making. A compromised or misbehaving service can return unexpected types, malicious content, or missing fields. Parse through a Pydantic model before use.
