# Security and operations

## Row-Level Security (RLS)

```sql
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders FORCE ROW LEVEL SECURITY;  -- applies to table owner too

-- Set session context (generic, no extensions needed)
SET app.current_user_id = '123';

CREATE POLICY orders_user_policy ON orders
  FOR ALL
  USING (user_id = current_setting('app.current_user_id')::bigint);
```

**Performance:** Policy expressions evaluate per row. Wrap function calls in a scalar subquery so PG evaluates once and caches:

```sql
-- BAD: called per row
USING (get_current_user() = user_id)
-- GOOD: evaluated once, cached
USING ((SELECT get_current_user()) = user_id)
```

Always index columns referenced in RLS policies. For complex multi-table checks, use `SECURITY DEFINER` helper functions.


## Concurrency Patterns

See [concurrency-patterns.md](./concurrency-patterns.md) for UPSERT, deadlock prevention, N+1 elimination, batch inserts, and queue processing with SKIP LOCKED.


## Partitioning

Use when table exceeds ~100M rows or needs TTL purge:
- `RANGE`: time-series (by month/year), most common
- `LIST`: categorical (by region, tenant)
- `HASH`: even distribution when no natural key

Partition key must be in every unique/PK constraint. Create indexes on partitions, not parent.

Foreign keys *from* a partitioned table need PG11+; foreign keys *referencing* a partitioned table need PG12+. On older versions enforce with triggers.


## Transactions & Locking

- Keep transactions short; long txns block vacuum and bloat tables
- Advisory locks for application-level mutual exclusion: `pg_advisory_xact_lock(key)`
- Non-blocking alternative: `pg_try_advisory_lock(key)` returns false instead of waiting
- **`pg_advisory_xact_lock()` called outside an open transaction is released immediately.** Under autocommit the call is its own transaction, so the lock is taken and dropped before the protected code runs, and every test still passes because nothing contends. Assert the nesting depth the lock was taken at, not that the call happened; a transaction-wrapping test harness already holds one, so depth 1 means the caller opened none. Reserve session-scoped `pg_advisory_lock()` for paths where the release sits on an unconditional cleanup.
- Check blocked queries: `SELECT * FROM pg_stat_activity WHERE wait_event_type = 'Lock'`
- Monitor deadlocks: `SELECT deadlocks FROM pg_stat_database WHERE datname = current_database()`
- **`SELECT ... FOR UPDATE` only locks rows that already exist**; it does not prevent a phantom insert of a missing row. Two transactions can both query a key, both see no row, both proceed to insert; the second fails the unique constraint (or both succeed if none existed). For a get-or-create / insert-if-missing race, `FOR UPDATE` is the wrong tool: use a partial unique index + `INSERT ... ON CONFLICT DO NOTHING/UPDATE`, or serialize the key with `pg_advisory_xact_lock(hashtext(:key))` before the existence check.
- **A unique-violation (SQLSTATE 23505) caught inside an open transaction can't continue in that same transaction**: once any statement raises, the transaction enters the aborted state and every later statement fails with `current transaction is aborted, commands ignored until end of transaction block`. Wrap the risky statement in a `SAVEPOINT` and `ROLLBACK TO SAVEPOINT` on error, or push the insert-or-update into a single `ON CONFLICT` statement that never raises. A bare try/catch around the failing statement is not enough on PostgreSQL.
- **A row lock orders the writes, not the reads that steer them.** A `FOR UPDATE` placed first in the transaction is still TOCTOU when the value deciding what the locked block writes was read *before* the lock and never re-read from the locked row; whichever transaction the lock lets through second is then the one applying work computed from a stale input. Re-read every steering value inside the lock; see [concurrency-patterns.md](./concurrency-patterns.md).
- **Inserting a child row takes `FOR KEY SHARE` on the parent it references**, and `FOR KEY SHARE` conflicts with `FOR UPDATE` alone. Locking the parent *before* the insert therefore serializes concurrent creators; locking it *after* the insert makes two concurrent runs of that same path deadlock against each other. `FOR SHARE` and `FOR NO KEY UPDATE` do not conflict with `KEY SHARE` and serialize nothing here; see [concurrency-patterns.md](./concurrency-patterns.md).
- **A nested `BEGIN` (or framework `transaction()` wrapper) becomes a `SAVEPOINT`, not an independent transaction**; only the outermost `BEGIN` is a real transaction. A per-iteration "transaction" inside an outer one does not commit independently and does not release row locks between iterations (held until the outer `COMMIT`); an unhandled inner error aborts the whole outer transaction. For a long backfill that needs per-row commit and lock release, run each unit as its own top-level transaction; don't nest it under an outer one.


## Full-Text Search

See [full-text-search.md](./full-text-search.md) for weighted tsvector setup, query syntax, highlighting, and when to use PG full-text vs external search.


## Connection Pooling

Always pool in production. Direct connections cost ~10MB each.
- PgBouncer in `transaction` mode for most workloads
- `statement` mode if no session-level features (prepared statements, temp tables, advisory locks)

**Prepared statement caveat:** Named prepared statements are bound to a specific connection. In transaction-mode pooling, the next request may hit a different connection. Use unnamed/extended-query-protocol statements (most ORMs default to this), or deallocate immediately after use.

See [performance-patterns.md](./performance-patterns.md) for the query shapes an index cannot serve, pool-exhaustion diagnosis (raising `max` relocates the queue), and cache discipline (stampede, negative caching, key completeness).


## Operations

See [operations.md](./operations.md) for performance tuning, maintenance/monitoring, WAL, replication, and backup/recovery.


## Vector Search (pgvector)

HNSW vs IVFFlat index choice, embedding column setup, pre-filtering, and distance operators: see [performance-patterns.md](./performance-patterns.md).
