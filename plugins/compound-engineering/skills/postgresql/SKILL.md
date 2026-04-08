---
name: postgresql
description: >-
  PostgreSQL schema design, query optimization, indexing, and administration.
  Use when working with PostgreSQL, JSONB, partitioning, RLS, CTEs, window
  functions, or EXPLAIN ANALYZE.
paths: "**/*.sql"
---

# PostgreSQL

## Data Type Defaults

| Need | Use | Avoid |
|------|-----|-------|
| Primary key | `BIGINT GENERATED ALWAYS AS IDENTITY` | `SERIAL`, `BIGSERIAL` |
| Timestamps | `TIMESTAMPTZ` | `TIMESTAMP` (loses timezone) |
| Text | `TEXT` | `VARCHAR(n)` unless constraint needed |
| Money | `NUMERIC(precision, scale)` | `MONEY`, `FLOAT` |
| Boolean | `BOOLEAN` with `NOT NULL DEFAULT` | nullable booleans |
| JSON | `JSONB` | `JSON` (no indexing), text JSON |
| UUID | `gen_random_uuid()` (PG13+) | `uuid-ossp` extension |
| IP addresses | `INET` / `CIDR` | text |
| Ranges | `TSTZRANGE`, `INT4RANGE`, etc. | pair of columns |

## Schema Rules

- Every FK column gets an index (PG does NOT auto-create these)
- `NOT NULL` on every column unless NULL has business meaning
- `CHECK` constraints for domain rules at DB level
- `EXCLUDE` constraints for range overlaps: `EXCLUDE USING gist (room WITH =, during WITH &&)`
- Default `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- Separate `updated_at` with trigger, never trust app layer alone
- Use `BIGINT` PKs -- cheaper JOINs than UUID, better index locality
- Safe migrations: `CREATE INDEX CONCURRENTLY`, add columns with `DEFAULT` (instant add). Never `ALTER TYPE` on large tables in-place.
- `NULLS NOT DISTINCT` on unique indexes (PG15+) -- treats NULLs as equal for uniqueness
- Revoke default public schema access: `REVOKE ALL ON SCHEMA public FROM public`

## Migration Safety

**Core rules:**
- Every schema change is a migration. No ad-hoc DDL in production.
- Migrations are immutable once deployed -- never edit a migration that has run in any shared environment.
- Schema migrations and data migrations are separate files. Schema changes are fast and transactional; data backfills are slow and may need batching.
- Forward-only in production. Rollback = a new forward migration that reverses the change.

**Expand-contract pattern** for zero-downtime renames and removals:

1. **Expand**: add the new column/table, backfill data, update writes to populate both old and new
2. **Migrate**: switch reads to the new column/table, verify in production
3. **Contract**: remove the old column/table in a later deploy

Never rename or remove a column in a single migration -- callers reading the old name will break between deploy and code rollout.

**Dangerous operations:**
- `NOT NULL` without a `DEFAULT` on an existing table locks and rewrites every row. Add the column nullable first, backfill, then add the constraint.
- `CREATE INDEX` (without `CONCURRENTLY`) locks writes for the duration. Always use `CONCURRENTLY`, which cannot run inside a transaction block -- keep it in its own migration.
- Large data backfills: batch with `FOR UPDATE SKIP LOCKED` to avoid locking the entire table:

```sql
UPDATE target SET new_col = compute(old_col)
WHERE id IN (
  SELECT id FROM target
  WHERE new_col IS NULL
  LIMIT 1000
  FOR UPDATE SKIP LOCKED
);
```

Run in a loop until zero rows affected.

## Index Strategy

| Type | Use When |
|------|----------|
| B-tree (default) | Equality, range, sorting, `LIKE 'prefix%'` |
| GIN | JSONB (`@>`, `?`, `?&`), arrays, full-text (`tsvector`) |
| GiST | Geometry, ranges, full-text (smaller but slower than GIN) |
| BRIN | Large tables with natural ordering (timestamps, serial IDs) |

**Index rules:**
- Composite: most selective column first, max 3-4 columns
- Partial: `WHERE status = 'active'` -- smaller, faster
- Covering: `INCLUDE (col)` -- avoids heap lookup
- Expression: `ON (lower(email))` -- for function-based WHERE
- `fillfactor = 70-90` on write-heavy tables -- reserves space for HOT updates, reducing index bloat
- Drop unused indexes: `SELECT * FROM pg_stat_user_indexes WHERE idx_scan = 0`

**Detect unindexed foreign keys:**
```sql
SELECT conrelid::regclass, a.attname
FROM pg_constraint c
JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
WHERE c.contype = 'f'
  AND NOT EXISTS (
    SELECT 1 FROM pg_index i
    WHERE i.indrelid = c.conrelid AND a.attnum = ANY(i.indkey)
  );
```

## JSONB Patterns

```sql
-- GIN index for containment queries
CREATE INDEX ON items USING gin (metadata);
SELECT * FROM items WHERE metadata @> '{"status": "active"}';

-- Expression index for specific key access
CREATE INDEX ON items ((metadata->>'category'));
SELECT * FROM items WHERE metadata->>'category' = 'electronics';
```

Prefer typed columns over JSONB for frequently queried, well-structured data. Use JSONB for truly dynamic/variable attributes.

Use `jsonb_path_ops` operator class for containment-only (`@>`) queries -- 2-3x smaller index. Use default `jsonb_ops` when key-existence (`?`, `?|`) is needed.

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

## Query Optimization

- Always `EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)` before optimizing
- `pg_stat_statements` for slow query detection: `SELECT query, mean_exec_time, calls FROM pg_stat_statements WHERE mean_exec_time > 100 ORDER BY mean_exec_time DESC LIMIT 20`
- Table bloat check: `SELECT relname, n_dead_tup, last_vacuum FROM pg_stat_user_tables WHERE n_dead_tup > 10000 ORDER BY n_dead_tup DESC`
- Sequential scan on large table -> add index or check `WHERE` for function wrapping
- High `rows removed by filter` -> index doesn't match predicate
- CTEs are inlined by default; use `MATERIALIZED`/`NOT MATERIALIZED` hints to control optimization
- Prefer `EXISTS` over `IN` for correlated subqueries
- Use `LATERAL JOIN` when subquery needs outer row reference
- Cursor pagination (`WHERE id > $last ORDER BY id LIMIT $n`) over `OFFSET`
- Approximate row counts: `SELECT reltuples FROM pg_class WHERE relname = 'table'` -- avoids full `count(*)` on large tables
- Materialized views for expensive aggregations: `REFRESH MATERIALIZED VIEW CONCURRENTLY` (needs unique index). Schedule refresh, not per-query.

## Concurrency Patterns

See [concurrency-patterns.md](./references/concurrency-patterns.md) for UPSERT, deadlock prevention, N+1 elimination, batch inserts, and queue processing with SKIP LOCKED.

## Partitioning

Use when table exceeds ~100M rows or needs TTL purge:
- `RANGE` -- time-series (by month/year), most common
- `LIST` -- categorical (by region, tenant)
- `HASH` -- even distribution when no natural key

Partition key must be in every unique/PK constraint. Create indexes on partitions, not parent.

## Transactions & Locking

- Keep transactions short -- long txns block vacuum and bloat tables
- Advisory locks for application-level mutual exclusion: `pg_advisory_xact_lock(key)`
- Non-blocking alternative: `pg_try_advisory_lock(key)` -- returns false instead of waiting
- Check blocked queries: `SELECT * FROM pg_stat_activity WHERE wait_event_type = 'Lock'`
- Monitor deadlocks: `SELECT deadlocks FROM pg_stat_database WHERE datname = current_database()`

## Full-Text Search

See [full-text-search.md](./references/full-text-search.md) for weighted tsvector setup, query syntax, highlighting, and when to use PG full-text vs external search.

## Connection Pooling

Always pool in production. Direct connections cost ~10MB each.
- PgBouncer in `transaction` mode for most workloads
- `statement` mode if no session-level features (prepared statements, temp tables, advisory locks)

**Prepared statement caveat:** Named prepared statements are bound to a specific connection. In transaction-mode pooling, the next request may hit a different connection. Use unnamed/extended-query-protocol statements (most ORMs default to this), or deallocate immediately after use.

## Operations

See [operations.md](./references/operations.md) for performance tuning, maintenance/monitoring, WAL, replication, and backup/recovery.

## Vector Search (pgvector)

```sql
CREATE EXTENSION vector;
ALTER TABLE items ADD COLUMN embedding vector(1536);  -- match your model's output dimensions

-- HNSW: better recall, higher memory. Default choice.
CREATE INDEX ON items USING hnsw (embedding vector_cosine_ops);

-- IVFFlat: lower memory for large datasets. Set lists = sqrt(row_count).
CREATE INDEX ON items USING ivfflat (embedding vector_cosine_ops) WITH (lists = 1000);
```

Always filter BEFORE vector search (use partial indexes or CTEs with pre-filtered rows). Distance operators: `<=>` cosine, `<->` L2, `<#>` inner product.

## Anti-Patterns

| Anti-Pattern | Fix |
|-------------|-----|
| `SELECT *` | List needed columns |
| N+1 queries in application loop | Use `JOIN`, `IN`, or batch fetch |
| `OFFSET` for pagination on large tables | Cursor pagination: `WHERE id > $last ORDER BY id LIMIT $n` |
| `count(*)` on large tables | Approximate: `SELECT reltuples FROM pg_class WHERE relname = 'table'` |
| Nullable booleans | `NOT NULL DEFAULT false` -- three-valued logic causes subtle bugs |
| Missing FK indexes | See detection query in Index Strategy above |
| `ORDER BY RANDOM()` | Use `TABLESAMPLE` or application-side shuffle |

**Detection queries:**

```sql
-- Slow queries (requires pg_stat_statements)
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE mean_exec_time > 100
ORDER BY mean_exec_time DESC LIMIT 20;

-- Table bloat (dead tuples awaiting vacuum)
SELECT relname, n_dead_tup, last_vacuum, last_autovacuum
FROM pg_stat_user_tables
WHERE n_dead_tup > 10000
ORDER BY n_dead_tup DESC;

-- Unused indexes (candidates for removal)
SELECT schemaname, relname, indexrelname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0 AND indexrelname NOT LIKE '%_pkey'
ORDER BY pg_relation_size(indexrelid) DESC;
```

## Verify

Run `EXPLAIN (ANALYZE, BUFFERS)` on changed queries. Confirm no sequential scans on large tables and no unindexed FK columns before declaring done.
