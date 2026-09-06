---
name: ia-postgresql
class: language
description: >-
  PostgreSQL schema design, query optimization, indexing, and administration.
  Use when working with PostgreSQL, JSONB, partitioning, RLS, CTEs, window
  functions, or EXPLAIN ANALYZE.
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
| Raw bytes (verbatim payload) | `BYTEA` | `JSONB`, `TEXT` -- both re-encode |

A spec that says "log the raw response" is asking for byte fidelity, and no text type provides it. `JSONB` reparses: it drops insignificant whitespace, sorts object keys, keeps only the last of duplicate keys, and rewrites numbers out of exponent notation (`1e0` -> `1`; trailing zeros in `1.00` do survive, so "all numeric forms collapse" overstates it). A non-JSON body cannot be stored at all and usually lands as `NULL`. `TEXT` rejects a NUL byte and any sequence invalid in the database encoding, so a binary or mis-encoded body errors instead of storing. Persist the bytes in `BYTEA` with the content type beside them, and add a parsed `JSONB` column separately when queries need one -- reading the column type as proof the body is kept is the review error.

## Schema Rules

- Every FK column gets an index (PG does NOT auto-create these)
- `NOT NULL` on every column unless NULL has business meaning
- `CHECK` constraints for domain rules at DB level
- `EXCLUDE` constraints for range overlaps: `EXCLUDE USING gist (room WITH =, during WITH &&)`
- Default `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- Separate `updated_at` with trigger, never trust app layer alone. Gate it with `WHEN (OLD.* IS DISTINCT FROM NEW.*)` so a no-op write neither fires the function nor bumps the timestamp -- on `BEFORE UPDATE` the row image is built before the trigger runs, so the comparison sees the caller's row, not the one the trigger is about to stamp.
- Use `BIGINT` PKs -- cheaper JOINs than UUID, better index locality
- Safe migrations: `CREATE INDEX CONCURRENTLY`, add columns with a **non-volatile** `DEFAULT` (instant add). Never `ALTER TYPE` on large tables in-place.
- A `DEFAULT` whose expression is `VOLATILE` rewrites the entire table under `ACCESS EXCLUSIVE`; only `IMMUTABLE`/`STABLE` defaults get the metadata-only fast path. Check before shipping the migration: `SELECT provolatile FROM pg_proc WHERE proname = 'gen_random_uuid';` -- `v` is volatile, `s`/`i` are not. So `DEFAULT 7` and `DEFAULT now()` are instant, `DEFAULT gen_random_uuid()` is a full rewrite; add the column nullable, backfill in batches, then set the default.
- `NULLS NOT DISTINCT` on unique indexes (PG15+) -- treats NULLs as equal for uniqueness
- A `UNIQUE` constraint proves *at most* one row per key, never *exactly* one. The lower bound has to come from elsewhere -- a `NOT NULL` FK from the covered side, a `CHECK`, or a seeding invariant -- so any docblock, MR description, or review conclusion of the form "the index is unique, therefore every X has exactly one Y" is unsound until that other source is named. The tell is the word *exactly*, or a downstream promise phrased as a universal. One query settles it: enumerate the domain and count the members with zero rows.
- Under `NULLS NOT DISTINCT`, a pre-flight duplicate check written with SQL `=` misses NULL/NULL collisions -- the index rejects the second row, but `NULL = NULL` evaluates to NULL (not true), so a self-join or `WHERE a.col = b.col` probe silently skips exactly the pairs the index will reject. Write the probe with `IS NOT DISTINCT FROM` so NULL/NULL compares as equal.
- `ORDER BY col DESC` puts NULLs FIRST (ASC puts them last), so a "keep the newest row" dedup written `ORDER BY updated_at DESC` picks the row whose timestamp is NULL. ORM `timestamps()` helpers typically create `created_at`/`updated_at` as nullable, so the exposure is routine rather than exotic. Pin the order (`ORDER BY updated_at DESC NULLS LAST, id DESC`) or make the column `NOT NULL`. MySQL's DESC default is the opposite (NULLS LAST), so a query ported between the two silently changes which row survives.
- Revoke default public schema access: `REVOKE ALL ON SCHEMA public FROM public`
- Derive every attribute at its own grain. A property of the parent -- a session, a day, an order -- computed from one child row lands on every child and is legitimately partial for most of them, so the aggregate disagrees with itself depending on which child is read. Put parent-scoped facts in a table keyed at the parent grain, populate them from the child the parent designates, and prefer a boundary observation (the last event's timestamp) over a count threshold.

## Migration Safety

**Core rules:**
- Every schema change is a migration. No ad-hoc DDL in production.
- Migrations are immutable once deployed -- never edit a migration that has run in any shared environment.
- Schema migrations and data migrations are separate files. Schema changes are fast and transactional; data backfills are slow and may need batching. Exception: when one transaction is what closes a rolling-deploy null window, do not split reflexively -- see the `ADD COLUMN` lock note under Dangerous operations for the table-size disposition.
- Forward-only in production. Rollback = a new forward migration that reverses the change.
- A re-run guard that checks one object (`IF EXISTS`-style early return on the main table) is a valid proxy for "everything already applied" **only** when the entire migration body runs in one transaction. PostgreSQL rolls `CREATE TABLE` / `CREATE TYPE` / `CREATE INDEX` (non-concurrent) / `CREATE FUNCTION` / `CREATE TRIGGER` / `ALTER TABLE` back together, so table-exists implies the rest committed. Any statement that cannot run inside a transaction -- `CREATE INDEX CONCURRENTLY`, `ALTER TYPE ... ADD VALUE` on older versions, `VACUUM` -- sits outside that guarantee, and the guard then skips it on re-run and ships a partial schema. Confirm every DDL object is inside the one transaction before relying on the guard.

**Expand-contract pattern** for zero-downtime renames and removals:

1. **Expand**: add the new column/table, backfill data, update writes to populate both old and new
2. **Migrate**: switch reads to the new column/table, verify in production
3. **Contract**: remove the old column/table in a later deploy

Never rename or remove a column in a single migration -- callers reading the old name will break between deploy and code rollout.

The transitional window covers every layer a client reads, not just the column. A migration can be flawlessly rolling-deploy-safe on the write side while the same release drops the field from the API response, and a bundle loaded before the deploy then reads `undefined` -- a render-time crash, not a graceful absence. Enumerate the field's treatment per layer (column, response payload, each client) and keep the response emitting it until the same later release that drops the column. "The client change ships alongside" addresses new bundles, not the ones already running.

**Dangerous operations:**
- `NOT NULL` without a `DEFAULT` on an existing table locks and rewrites every row. Add the column nullable first, backfill, then add the constraint.
- `CREATE INDEX` (without `CONCURRENTLY`) locks writes for the duration. Always use `CONCURRENTLY`, which cannot run inside a transaction block -- keep it in its own migration.
- `ADD COLUMN ... NULL` with no default is metadata-only and fast, but it takes `ACCESS EXCLUSIVE` and that lock is held until the enclosing **transaction** commits -- not until the `ALTER` returns. A migration that adds the column and then backfills every row in the same transaction blocks all readers and writers for the backfill's duration. Do not reflexively split it: the single-transaction ordering (`ADD` nullable -> backfill -> `SET DEFAULT`) is itself the fix for the rolling-deploy window where an old release inserts `NULL` before the default exists. The disposition is table size, not a rule -- on a small table accept the sub-second hold and state the row count; on a large one use expand-contract (deploy the column with a constant `DEFAULT` first, then a separate chunked backfill outside a transaction).
- A dedup pass preceding a **partial** unique index must carry the index's own predicate. `CREATE UNIQUE INDEX ... WHERE <pred>` constrains only the rows matching `<pred>`, but a dedup that ranks over the whole table collapses each key to a single row and hard-deletes `<pred>`-failing rows the index would have allowed -- silent data loss on a forward-only migration. Put `<pred>` inside the ranked subquery, and compare the delete's row count against a `SELECT count(*) ... WHERE NOT <pred>` before committing.
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

**Full-replace clobber on read-modify-write loops.** A migration that loops `SELECT col → mutate in app → UPDATE SET col = new_full_value WHERE id = ?` silently drops concurrent writes that landed between SELECT and UPDATE. Any column written by live traffic is exposed: `jsonb` documents, comma-separated tag fields, denormalized counters, JSON-encoded attribute blobs. Mitigations, in order of preference:

- **In-place atomic update** when the edit is expressible as SQL: `UPDATE t SET col = jsonb_set(col, '{path}', :value) WHERE ...`, or `UPDATE t SET tags = array_append(tags, :tag) WHERE ...` — no read-modify-write window.
- **Row-level lock during the loop:** wrap each iteration in a transaction, `SELECT ... WHERE id = ? FOR UPDATE`, then mutate and write. Cheaper to author, accepts more lock contention.
- **Compare-and-swap retry:** include the original snapshot in `WHERE col = :original_value`, check the affected-row count; on 0, re-read and retry. Robust under contention, requires explicit retry-loop handling.

Default chunked decode-encode loops are only safe during a maintenance window with writes blocked. ORM "chunkById + load + mutate + save" patterns hit this same trap.

**A SQL backfill claiming parity with an application normalizer usually differs on a character class.** One-argument `btrim(x)` trims spaces only, while PHP's `trim()` and Python's `.strip()` trim the whole ASCII whitespace set -- so a value carrying a tab folds out of vocabulary in SQL, and on a value-dropping migration that is one-way data loss. Pass the character set explicitly (`btrim(x, E' \t\n\r\x0B')`, which mirrors PHP's default) and apply it to the blank guard as well as the comparison. Whenever a query re-implements an application normalizer, enumerate every class each side treats as insignificant -- whitespace, case folding, Unicode normalization, trailing punctuation -- and execute both over the same inputs, loading the committed implementation verbatim rather than retyping it.

**Rollback fidelity is executable.** Reviewers compare the up and down SQL as strings and agree they look symmetric, which misses a renamed index, a dropped partial predicate, or an operator-class difference. Hold the migration out and build the baseline, restore and apply it, roll back one step, then diff the catalog's normalized output (`pg_indexes.indexdef`, `pg_get_constraintdef(oid)`); an empty diff is the answer, and no amount of reading is. Run it on anything that rebuilds a unique or partial index, or re-keys an index in place.

## Index Strategy

| Type | Use When |
|------|----------|
| B-tree (default) | Equality, range, sorting, `LIKE 'prefix%'` |
| GIN | JSONB (`@>`, `?`, `?&`), arrays, full-text (`tsvector`) |
| GiST | Geometry, ranges, full-text (smaller but slower than GIN) |
| BRIN | Large tables with natural ordering (timestamps, serial IDs) |

**Index rules:**
- Composite: equality-predicate columns first, then the range/sort column, max 3-4 columns -- a leading range column stops the B-tree from navigating on anything after it. "Most selective first" is the myth version; selectivity only breaks ties among equality columns
- Partial: `WHERE status = 'active'` -- smaller, faster, and it constrains *only* the rows matching the predicate. A plain unique index likewise constrains only rows whose key columns are all non-NULL, since NULLs compare as distinct unless the index is `NULLS NOT DISTINCT`. So a "prevent duplicates" index validated against the new write path enforces nothing against an existing writer that leaves a key column NULL or writes rows the predicate excludes, and the dedup the migration promises is leaky for exactly those rows. Audit every writer of the table, not the one in the diff
- Covering: `INCLUDE (col)` -- avoids heap lookup
- Expression: `ON (lower(email))` -- for function-based WHERE
- A GIN index on an array column serves the containment operators, not `=`: `WHERE 'x' = ANY(col)` seq-scans even with `enable_seqscan = off`, because `ANY` over an array expands to equality and no GIN operator class implements it. Write the predicate as `WHERE col @> ARRAY['x']` to reach the index.
- `fillfactor = 70-90` on write-heavy tables -- reserves space for HOT updates, reducing index bloat
- Drop unused indexes (only after one full business cycle since last restart -- check `pg_stat_database.stats_reset` first, otherwise you may drop a primary key on a freshly restarted DB or read replica): `SELECT * FROM pg_stat_user_indexes WHERE idx_scan = 0`

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

**Delete operators:**

| Operator | Operand | Behavior | Example |
|----------|---------|----------|---------|
| `-` | text | remove top-level key from object | `'{"a":1,"b":2}'::jsonb - 'a'` → `{"b":2}` |
| `-` | text[] | remove multiple top-level keys | `'{"a":1,"b":2}'::jsonb - ARRAY['a','b']` → `{}` |
| `-` | integer | remove array element by index | `'[1,2,3]'::jsonb - 1` → `[1,3]` |
| `#-` | text[] | remove value at nested path | `'{"a":{"b":1}}'::jsonb #- '{a,b}'` → `{"a":{}}` |

Common mistakes:

- `col - 'a,b'` treats `'a,b'` as a single key name (no-op against a normally-structured document — the comma isn't a path separator).
- `col - 'a' - 'b'` first removes the entire `a` subtree before attempting `- 'b'` on the result (data loss of `a.*`, then a no-op).
- `jsonb_set(col, '{a,b}', 'null'::jsonb)` sets the value to JSON `null` rather than removing the key — strict "key absent" checks downstream then fail. Worse: `jsonb_set(col, '{a,b}', NULL)` with a bare SQL `NULL` makes the STRICT function return SQL `NULL`, clobbering the entire column on update. To delete the key, use `#-`; to set it explicitly to JSON null, use `'null'::jsonb` (and know that's distinct from absence).

For nested deletes, use `#-` with a text-array path. Verify with one round-tripped row of the worst-case shape before committing the migration: `SELECT col #- '{a,b}' FROM t WHERE id = ? LIMIT 1`, then confirm the key is gone (not present-as-null, no sibling data loss).

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
- Use `pg_stat_statements` for slow-query detection and `pg_stat_user_tables` for bloat (see [operations.md](./references/operations.md) for the full SQL)
- Sequential scan on large table -> add index or check `WHERE` for function wrapping
- High `rows removed by filter` -> index doesn't match predicate
- CTEs are inlined by default; use `MATERIALIZED`/`NOT MATERIALIZED` hints to control optimization
- Prefer `EXISTS` over `IN` for correlated subqueries
- Use `LATERAL JOIN` when subquery needs outer row reference
- Cursor pagination (`WHERE id > $last ORDER BY id LIMIT $n`) over `OFFSET`
- Approximate row counts: `SELECT reltuples FROM pg_class WHERE relname = 'table'` -- avoids full `count(*)` on large tables
- Materialized views for expensive aggregations: `REFRESH MATERIALIZED VIEW CONCURRENTLY` (needs unique index). Schedule refresh, not per-query.
- Anchor a time bucket to the domain's own boundary, not to the epoch. `date_bin(stride, ts, origin)` lays the grid down at `origin`, and `date_trunc` is calendar-anchored, so a stride that does not divide the gap between domain boundaries produces a bucket straddling one; grouping by that bucket plus a row-derived day then emits two rows per bucket and violates an `(entity, bucket_start)` primary key. Pass the domain boundary as `origin`, key on `(entity, bucket_start)`, and derive the day from the bucket rather than from the row.

## Concurrency Patterns

See [concurrency-patterns.md](./references/concurrency-patterns.md) for UPSERT, deadlock prevention, N+1 elimination, batch inserts, and queue processing with SKIP LOCKED.

## Partitioning

Use when table exceeds ~100M rows or needs TTL purge:
- `RANGE` -- time-series (by month/year), most common
- `LIST` -- categorical (by region, tenant)
- `HASH` -- even distribution when no natural key

Partition key must be in every unique/PK constraint. Create indexes on partitions, not parent.

Foreign keys *from* a partitioned table need PG11+; foreign keys *referencing* a partitioned table need PG12+ -- on older versions enforce with triggers.

## Transactions & Locking

- Keep transactions short -- long txns block vacuum and bloat tables
- Advisory locks for application-level mutual exclusion: `pg_advisory_xact_lock(key)`
- Non-blocking alternative: `pg_try_advisory_lock(key)` -- returns false instead of waiting
- **`pg_advisory_xact_lock()` called outside an open transaction is released immediately.** Under autocommit the call is its own transaction, so the lock is taken and dropped before the protected code runs, and every test still passes because nothing contends. Assert the nesting depth the lock was taken at, not that the call happened -- a transaction-wrapping test harness already holds one, so depth 1 means the caller opened none. Reserve session-scoped `pg_advisory_lock()` for paths where the release sits on an unconditional cleanup.
- Check blocked queries: `SELECT * FROM pg_stat_activity WHERE wait_event_type = 'Lock'`
- Monitor deadlocks: `SELECT deadlocks FROM pg_stat_database WHERE datname = current_database()`
- **`SELECT ... FOR UPDATE` only locks rows that already exist** -- it does not prevent a phantom insert of a missing row. Two transactions can both query a key, both see no row, both proceed to insert; the second fails the unique constraint (or both succeed if none existed). For a get-or-create / insert-if-missing race, `FOR UPDATE` is the wrong tool -- use a partial unique index + `INSERT ... ON CONFLICT DO NOTHING/UPDATE`, or serialize the key with `pg_advisory_xact_lock(hashtext(:key))` before the existence check.
- **A unique-violation (SQLSTATE 23505) caught inside an open transaction can't continue in that same transaction** -- once any statement raises, the transaction enters the aborted state and every later statement fails with `current transaction is aborted, commands ignored until end of transaction block`. Wrap the risky statement in a `SAVEPOINT` and `ROLLBACK TO SAVEPOINT` on error, or push the insert-or-update into a single `ON CONFLICT` statement that never raises. A bare try/catch around the failing statement is not enough on PostgreSQL.
- **A row lock orders the writes, not the reads that steer them.** A `FOR UPDATE` placed first in the transaction is still TOCTOU when the value deciding what the locked block writes was read *before* the lock and never re-read from the locked row -- whichever transaction the lock lets through second is then the one applying work computed from a stale input. Re-read every steering value inside the lock; see [concurrency-patterns.md](./references/concurrency-patterns.md).
- **Inserting a child row takes `FOR KEY SHARE` on the parent it references**, and `FOR KEY SHARE` conflicts with `FOR UPDATE` alone. Locking the parent *before* the insert therefore serializes concurrent creators; locking it *after* the insert makes two concurrent runs of that same path deadlock against each other. `FOR SHARE` and `FOR NO KEY UPDATE` do not conflict with `KEY SHARE` and serialize nothing here -- see [concurrency-patterns.md](./references/concurrency-patterns.md).
- **A nested `BEGIN` (or framework `transaction()` wrapper) becomes a `SAVEPOINT`, not an independent transaction** -- only the outermost `BEGIN` is a real transaction. A per-iteration "transaction" inside an outer one does not commit independently and does not release row locks between iterations (held until the outer `COMMIT`); an unhandled inner error aborts the whole outer transaction. For a long backfill that needs per-row commit and lock release, run each unit as its own top-level transaction -- don't nest it under an outer one.

## Full-Text Search

See [full-text-search.md](./references/full-text-search.md) for weighted tsvector setup, query syntax, highlighting, and when to use PG full-text vs external search.

## Connection Pooling

Always pool in production. Direct connections cost ~10MB each.
- PgBouncer in `transaction` mode for most workloads
- `statement` mode if no session-level features (prepared statements, temp tables, advisory locks)

**Prepared statement caveat:** Named prepared statements are bound to a specific connection. In transaction-mode pooling, the next request may hit a different connection. Use unnamed/extended-query-protocol statements (most ORMs default to this), or deallocate immediately after use.

See [performance-patterns.md](./references/performance-patterns.md) for the query shapes an index cannot serve, pool-exhaustion diagnosis (raising `max` relocates the queue), and cache discipline (stampede, negative caching, key completeness).

## Operations

See [operations.md](./references/operations.md) for performance tuning, maintenance/monitoring, WAL, replication, and backup/recovery.

## Vector Search (pgvector)

HNSW vs IVFFlat index choice, embedding column setup, pre-filtering, and distance operators: see [performance-patterns.md](./references/performance-patterns.md).

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

Detection queries for slow queries, table bloat, and unused indexes: see [operations.md](./references/operations.md).

## Verify

Run `EXPLAIN (ANALYZE, BUFFERS)` on changed queries. Confirm no sequential scans on large tables and no unindexed FK columns before declaring done.
