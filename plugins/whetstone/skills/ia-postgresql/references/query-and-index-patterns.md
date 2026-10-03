# Query and index patterns

## Index Strategy

| Type | Use When |
|------|----------|
| B-tree (default) | Equality, range, sorting, `LIKE 'prefix%'` |
| GIN | JSONB (`@>`, `?`, `?&`), arrays, full-text (`tsvector`) |
| GiST | Geometry, ranges, full-text (smaller but slower than GIN) |
| BRIN | Large tables with natural ordering (timestamps, serial IDs) |

**Index rules:**
- Composite: equality-predicate columns first, then the range/sort column, max 3-4 columns. A leading range column stops the B-tree from navigating on anything after it. "Most selective first" is the myth version; selectivity only breaks ties among equality columns
- Partial: `WHERE status = 'active'` is smaller, faster, and constrains *only* the rows matching the predicate. A plain unique index likewise constrains only rows whose key columns are all non-NULL, since NULLs compare as distinct unless the index is `NULLS NOT DISTINCT`. So a "prevent duplicates" index validated against the new write path enforces nothing against an existing writer that leaves a key column NULL or writes rows the predicate excludes, and the dedup the migration promises is leaky for exactly those rows. Audit every writer of the table, not the one in the diff
- Covering: `INCLUDE (col)` avoids heap lookup
- Expression: `ON (lower(email))` for function-based WHERE
- A GIN index on an array column serves the containment operators, not `=`: `WHERE 'x' = ANY(col)` seq-scans even with `enable_seqscan = off`, because `ANY` over an array expands to equality and no GIN operator class implements it. Write the predicate as `WHERE col @> ARRAY['x']` to reach the index.
- `fillfactor = 70-90` on write-heavy tables reserves space for HOT updates, reducing index bloat
- Drop unused indexes (only after one full business cycle since last restart; check `pg_stat_database.stats_reset` first; on a freshly restarted DB or read replica, `idx_scan = 0` reports live indexes, primary keys included, as unused): `SELECT * FROM pg_stat_user_indexes WHERE idx_scan = 0`

**Find foreign keys without a valid unfiltered B-tree key prefix (PostgreSQL 11+):**
```sql
SELECT c.conrelid::regclass AS table_name, c.conname,
       pg_get_constraintdef(c.oid) AS foreign_key
FROM pg_constraint c
WHERE c.contype = 'f'
  AND NOT EXISTS (
    SELECT 1 FROM pg_index i
    JOIN pg_class idx ON idx.oid = i.indexrelid
    JOIN pg_am am ON am.oid = idx.relam
    WHERE i.indrelid = c.conrelid
      AND i.indisvalid AND i.indisready
      AND i.indpred IS NULL
      AND am.amname = 'btree'
      AND i.indnkeyatts >= cardinality(c.conkey)
      AND ARRAY(
        SELECT k.attnum
        FROM unnest(i.indkey) WITH ORDINALITY AS k(attnum, position)
        WHERE k.position <= cardinality(c.conkey)
        ORDER BY k.attnum
      ) = ARRAY(SELECT fk.attnum FROM unnest(c.conkey) AS fk(attnum) ORDER BY fk.attnum)
  );
```

Treat results as review candidates: a partial index can cover the required referencing rows when its predicate is guaranteed by the FK lookup, and other access methods need separate evaluation. Verify predicate coverage and the actual lookup plan before adding an index. `INCLUDE` payloads are not search keys; separate single-column indexes do not establish one complete composite-FK prefix.


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

Use `jsonb_path_ops` operator class for containment-only (`@>`) queries: 2-3x smaller index. Use default `jsonb_ops` when key-existence (`?`, `?|`) is needed.

**Delete operators:**

| Operator | Operand | Behavior | Example |
|----------|---------|----------|---------|
| `-` | text | remove top-level key from object | `'{"a":1,"b":2}'::jsonb - 'a'` → `{"b":2}` |
| `-` | text[] | remove multiple top-level keys | `'{"a":1,"b":2}'::jsonb - ARRAY['a','b']` → `{}` |
| `-` | integer | remove array element by index | `'[1,2,3]'::jsonb - 1` → `[1,3]` |
| `#-` | text[] | remove value at nested path | `'{"a":{"b":1}}'::jsonb #- '{a,b}'` → `{"a":{}}` |

Common mistakes:

- `col - 'a,b'` treats `'a,b'` as a single key name (no-op against a normally-structured document; the comma isn't a path separator).
- `col - 'a' - 'b'` first removes the entire `a` subtree before attempting `- 'b'` on the result (data loss of `a.*`, then a no-op).
- `jsonb_set(col, '{a,b}', 'null'::jsonb)` sets the value to JSON `null` rather than removing the key, so strict "key absent" checks downstream then fail. Worse: `jsonb_set(col, '{a,b}', NULL)` with a bare SQL `NULL` makes the STRICT function return SQL `NULL`, clobbering the entire column on update. To delete the key, use `#-`; to set it explicitly to JSON null, use `'null'::jsonb` (and know that's distinct from absence).
- `jsonb_set_lax(col, path, :value)` (PG 13+) is the NULL-tolerant variant for a nullable bound parameter: its default `null_value_treatment => 'use_json_null'` writes JSON `null`, `'delete_key'` removes the key, and `'return_target'` leaves the document unchanged, so an SQL `NULL` no longer wipes the column.

For nested deletes, use `#-` with a text-array path. Verify with one round-tripped row of the worst-case shape before committing the migration: `SELECT col #- '{a,b}' FROM t WHERE id = ? LIMIT 1`, then confirm the key is gone (not present-as-null, no sibling data loss).


## Query Optimization

- Always `EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)` before optimizing
- Pin the plan as a regression assertion, not only a one-time diagnostic. For a hot-path query whose performance depends on a specific access method, assert the plan in an automated test: a migration that drops an index, or a rewrite that makes a predicate non-sargable (`WHERE lower(email) = ...` against a plain index, `WHERE col + 0 = ...`), silently regresses the query from an index scan to a sequential scan while every result-correctness test still passes. Plan text is not stable across minor versions and configuration (`work_mem`, `random_page_cost`, table statistics), so never string-match the whole plan; use `EXPLAIN (FORMAT JSON)` and assert on the node type: `Index Scan` or `Index Only Scan` on the expected index name, or the absence of `Seq Scan` on the target relation. Run it against a fixture with enough rows that the planner's choice is not dominated by table size; a planner on a 10-row table legitimately prefers a seq scan.
- Use `pg_stat_statements` for slow-query detection and `pg_stat_user_tables` for bloat (see [operations.md](./operations.md) for the full SQL)
- Sequential scan on large table -> add index or check `WHERE` for function wrapping
- High `rows removed by filter` -> index doesn't match predicate
- CTEs are inlined by default; use `MATERIALIZED`/`NOT MATERIALIZED` hints to control optimization
- Prefer `EXISTS` over `IN` for correlated subqueries
- Use `LATERAL JOIN` when subquery needs outer row reference
- Cursor pagination (`WHERE id > $last ORDER BY id LIMIT $n`) over `OFFSET`
- Per-key snapshot plus keyset pagination over settled rows. A windowed query returns at most N rows per key without N+1 queries; its scan work still depends on the source rows and plan:
  ```sql
  -- bootstrap: at most 50 rows per account, newest first
  SELECT id, account_id, payload
  FROM (
    SELECT e.*, row_number() OVER (PARTITION BY account_id ORDER BY id DESC) AS rn
    FROM events e
  ) ranked
  WHERE rn <= 50;
  -- keyset page: safe for settled rows or a proven commit-ordered watermark
  SELECT id, account_id, payload FROM events
  WHERE id > :cursor ORDER BY id ASC LIMIT :n;
  ```
  Limit the known key set in the inner query with `WHERE account_id IN (...)` and inspect the plan. A sequence or identity orders allocation, not commits: transaction A can allocate 100, B commit 101, the reader advance to 101, and A later commit 100 below the cursor. For lossless live catch-up, establish a snapshot/CDC handoff with a commit-ordered position, or use overlap, deduplication, and reconciliation that explicitly covers late commits. A finite overlap is sufficient only with a proven bound on lateness. Do not treat the maximum observed ID or a timestamp as that proof; retain simple ID keyset pagination for settled datasets or listings that accept concurrent omissions.
- Approximate row counts: `SELECT reltuples FROM pg_class WHERE relname = 'table'` avoids full `count(*)` on large tables
- Materialized views for expensive aggregations: `REFRESH MATERIALIZED VIEW CONCURRENTLY` (needs unique index). Schedule refresh, not per-query.
- Anchor a time bucket to the domain's own boundary, not to the epoch. `date_bin(stride, ts, origin)` lays the grid down at `origin`, and `date_trunc` is calendar-anchored, so a stride that does not divide the gap between domain boundaries produces a bucket straddling one; grouping by that bucket plus a row-derived day then emits two rows per bucket and violates an `(entity, bucket_start)` primary key. Pass the domain boundary as `origin`, key on `(entity, bucket_start)`, and derive the day from the bucket rather than from the row.


## Anti-Patterns

| Anti-Pattern | Fix |
|-------------|-----|
| `SELECT *` | List needed columns |
| N+1 queries in application loop | Use `JOIN`, `IN`, or batch fetch |
| `OFFSET` for pagination on large tables | Cursor pagination: `WHERE id > $last ORDER BY id LIMIT $n` |
| `count(*)` on large tables | Approximate: `SELECT reltuples FROM pg_class WHERE relname = 'table'` |
| Nullable booleans | `NOT NULL DEFAULT false`; three-valued logic causes subtle bugs |
| Missing FK indexes | See detection query in Index Strategy above |
| `ORDER BY RANDOM()` | Use `TABLESAMPLE` or application-side shuffle |

Detection queries for slow queries, table bloat, and unused indexes: see [operations.md](./operations.md).
