# Performance Patterns -- When Indexes Can't Help, Pools, and Caching

## When an index cannot help

Adding an index is the reflex fix; these four query shapes defeat it. Recognize them before recommending an index that will never be used.

| Shape | Why the index is dead | Fix |
|-------|----------------------|-----|
| Function on the column: `WHERE lower(email) = ?` | The stored values are indexed, not the function's output | Expression index `ON (lower(email))`, or generated column |
| Leading wildcard: `LIKE '%term'` | B-tree matches prefixes only | Trigram GIN (`pg_trgm`) or full-text search |
| Type mismatch: `WHERE varchar_col = 123` | The implicit cast wraps the column, same as a function | Match the literal's type to the column |
| Low selectivity: predicate matches a large fraction of rows | The planner correctly prefers a seq scan; forcing the index is slower | Partial index on the rare value, or accept the seq scan |

Confirm with `EXPLAIN (ANALYZE, BUFFERS)` -- an index that exists but never appears in the plan is one of these shapes, not a planner bug.

## Pool exhaustion: relocating the queue is not fixing it

When requests wait on connections, raising the application pool's `max` is usually the wrong move:

- Postgres does non-trivial work per connection (~10MB, a backend process). An application pool sized above what the database can concurrently execute just moves the wait from the app's pool queue into the database, where it costs memory and context switches.
- Diagnose before resizing: `SELECT state, count(*) FROM pg_stat_activity GROUP BY state`. Many `idle in transaction` sessions mean the app holds connections across non-DB work (HTTP calls, file I/O inside a transaction) -- fix the transaction scope, not the pool.
- Sizing start point: connections ≈ cores × 2 for CPU-bound OLTP. If the app tier needs more concurrent requests than that, multiplex through PgBouncer in `transaction` mode rather than raising `max_connections`.
- One pool per service instance multiplies: 20 instances × pool max 20 = 400 connections. Size the fleet, not the process.

## Cache discipline (application-side, for query results)

- **Stampede protection.** When a hot key expires, every concurrent request recomputes it and hits the database at once. Use request coalescing (first caller computes, the rest wait on that computation) or stale-while-revalidate (serve the expired value while one background refresh runs). TTL jitter (±10%) prevents synchronized expiry across keys.
- **Negative caching.** Cache "not found" results with a short TTL. Without it, requests for missing rows bypass the cache forever -- a scraper enumerating IDs turns every miss into a query.
- **Cache-key completeness.** Every input that changes the response belongs in the key: tenant, locale, role/permission set, API version, feature flags. A key missing one of these serves one user's data to another; the bug presents as intermittent wrong data, not as an error.
- **Invalidate on write, don't trust TTL alone.** TTL bounds staleness; it does not provide correctness for read-after-write paths the user observes.
