# Observability: tracing, sampling, and telemetry governance

Read this when adding or reviewing OpenTelemetry spans, choosing where sampling happens, budgeting metric labels, or deciding which request data may enter telemetry at all. Signal selection, RED metrics, and structured logging live in [async-and-production.md](./async-and-production.md).

## Span kind

Pick the kind by the relationship to the remote side, not by the layer of the code:

- **SERVER** -- handling an inbound request while the caller waits (HTTP handler, gRPC method).
- **CLIENT** -- an outbound call where this process waits for the answer (HTTP fetch, DB query, cache lookup).
- **PRODUCER** -- enqueuing or scheduling work whose outcome this span does not wait for (publish to SQS/Kafka, `queue.add()`).
- **CONSUMER** -- processing work a producer handed off (job handler, message listener).
- **INTERNAL** -- in-process work with no remote parent or child (default). Service-layer methods are INTERNAL; do not mark them SERVER because they run "inside the server".

## HTTP status to span status

The rule is asymmetric by span kind, and the common mistake is marking every 4xx as an error:

- 1xx/2xx/3xx: leave span status UNSET on both kinds. Set ERROR only when a transport or protocol failure occurred (connection reset, redirect limit exceeded).
- 4xx: on a **SERVER** span, leave status UNSET -- the server behaved correctly by rejecting the request. On the matching **CLIENT** span, set ERROR -- this process sent a request the remote refused.
- 5xx (and any status the client cannot interpret): set ERROR on both kinds.
- Omit the status description when `http.response.status_code` already says why; put the status code number (as a string) in `error.type`.
- A request the caller cancelled on purpose (`AbortSignal`) is not an error: leave status UNSET and do not set `error.type`.

## Sample in the Collector, not in the SDK

Leave the application SDK on `AlwaysOn` (the default is `ParentBased(root=AlwaysOn)`) and make every sampling decision in the OpenTelemetry Collector (tail sampling). An SDK-side ratio sampler (`OTEL_TRACES_SAMPLER=traceidratio`) decides at span start, before latency or outcome is known, so it drops slow and failed traces at the same rate as healthy ones; the Collector sees the finished trace and can keep every error and every slow trace while downsampling the rest. If SDK sampling is unavoidable, keep a `parentbased_*` sampler so a trace is never half-sampled across services.

## Metric cardinality budget

Series count for one metric = product of the distinct value counts of every attribute x number of emitting instances. `http.request.method` (8) x `http.route` (60) x `http.response.status_code` (15) x 12 pods = 86,400 series for one histogram before bucket multiplication. Rough guide per metric: under 1,000 is free; 10,000 is normal for a fleet-wide request histogram; 100,000 needs a named owner and a backend cost check; any unbounded attribute (user ID, request ID, raw URL path, e-mail, session token, free text) is a defect at any scale because its value set grows with traffic, not with the code. Use `http.route` (the matched template), never the concrete path.

## Never-instrument list

These must not appear in span attributes, metric labels, log fields, or baggage under any name, hashed or truncated included: credentials and passwords; API keys, session tokens, `Authorization`/`Cookie`/`Set-Cookie` header values; payment card numbers, CVV, bank account numbers; government identifiers (SSN, passport, tax ID); health records and diagnoses; biometric data. Capture headers by allowlist only, never "all headers minus a denylist". Request and response bodies stay off; when a body field is genuinely needed, record a redacted, schema-validated projection, not the raw payload.
