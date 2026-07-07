# Anti-Patterns: Extended Notes

Detail offloaded from the SKILL.md Anti-Patterns section. The symptom/fix one-liners live inline; this file holds the mechanics, root-cause narratives, and fix ladders.

## Persistent test infrastructure state contamination

**Root cause:** persistent test infrastructure -- a long-running `docker compose up`, a shared local database, a volume left between iterations -- accumulates state across test runs. The current run's data sits on top of the previous run's data; assertions counting rows or jobs see the sum. The numbers look like a code bug ("the loop runs N times instead of once"), but they are clean integer multiples of the expected value, and the same test passes in CI on a fresh container.

**Fix ladder**, in order of preference:

1. **Ephemeral containers per test session** (`testcontainers`, `pytest-postgresql`, or `docker compose run --rm <service>` for one-shot runs) -- slowest to start, strongest isolation. Default for CI.
2. **Fixture-driven `TRUNCATE` / `DROP DATABASE`** in a session-scoped or per-test fixture -- fast, but requires careful coverage of every stateful table.
3. **Volume teardown between iterations** (`docker compose down -v` before each run) when running locally -- manual but reliable.

Never rely on tests "cleaning up after themselves." If a previous run errored mid-test, the cleanup didn't run, and the next run inherits the partial state.

## Synchronous adapters hide timing-dependent races

**Wire-latency mechanics:** a test fires two or more parallel requests through a mock/adapter that resolves synchronously (a promise that settles in the same microtask, an in-memory fake with zero latency) and asserts a coalescing/dedup/single-flight guard held. It passes -- but only because every call observed the shared in-flight state before any reset ran. Under real wire latency the staggered arrivals miss the window, and the guard spawns N operations instead of one.

Same-tick microtask concurrency is not a proxy for production burst behavior. For dedup/coalescing logic, inject controllable latency (fake timers, deferred resolution staggered across ticks) so a later arrival lands after the reset, and assert the guard holds for arrival-staggered bursts.

## Constructing the object-under-test below the layer that transforms it

**Extended rationale:** when a fix guards or transforms a field in an upstream layer (a parser, normalizer, `from_api_response` constructor, serializer) and the test builds the object directly via the leaf constructor -- `Model(field=x)`, `new T(...)`, the raw initializer -- the test injects the already-correct value. The upstream strip/transform never runs, the guard never fires, and the test is green while production is still broken. The test cannot fail for the exact bug it was written to catch.

Enter through the same entry point production uses. If a test must construct the leaf form directly for other reasons, it is not covering the transform; add a separate test that feeds the pre-transform input (the raw API payload, the unparsed dict) so the transform under test executes.
