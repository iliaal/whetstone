# Schema and migration safety

## Schema Rules

- Every FK column gets an index (PG does NOT auto-create these)
- `NOT NULL` on every column unless NULL has business meaning
- `CHECK` constraints for domain rules at DB level
- `EXCLUDE` constraints for range overlaps: `EXCLUDE USING gist (room WITH =, during WITH &&)`
- Default `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- Separate `updated_at` with trigger, never trust app layer alone. Gate it with `WHEN (OLD.* IS DISTINCT FROM NEW.*)` so a no-op write neither fires the function nor bumps the timestamp. On `BEFORE UPDATE` the row image is built before the trigger runs, so the comparison sees the caller's row, not the one the trigger is about to stamp.
- Use `BIGINT` PKs: cheaper JOINs than UUID, better index locality
- Safe migrations: `CREATE INDEX CONCURRENTLY`, add columns with a **non-volatile** `DEFAULT` (instant add). Never `ALTER TYPE` on large tables in-place.
- A `DEFAULT` whose expression is `VOLATILE` rewrites the entire table under `ACCESS EXCLUSIVE`; only `IMMUTABLE`/`STABLE` defaults get the metadata-only fast path. Check before shipping the migration: `SELECT provolatile FROM pg_proc WHERE proname = 'gen_random_uuid';` (`v` is volatile, `s`/`i` are not). So `DEFAULT 7` and `DEFAULT now()` are instant, `DEFAULT gen_random_uuid()` is a full rewrite; add the column nullable, backfill in batches, then set the default.
- `NULLS NOT DISTINCT` on unique indexes (PG15+) treats NULLs as equal for uniqueness
- A `UNIQUE` constraint proves *at most* one row per key, never *exactly* one. The lower bound has to come from elsewhere (a `NOT NULL` FK from the covered side, a `CHECK`, or a seeding invariant), so any docblock, MR description, or review conclusion of the form "the index is unique, therefore every X has exactly one Y" is unsound until that other source is named. The tell is the word *exactly*, or a downstream promise phrased as a universal. One query settles it: enumerate the domain and count the members with zero rows.
- Under `NULLS NOT DISTINCT`, a pre-flight duplicate check written with SQL `=` misses NULL/NULL collisions: the index rejects the second row, but `NULL = NULL` evaluates to NULL (not true), so a self-join or `WHERE a.col = b.col` probe silently skips exactly the pairs the index will reject. Write the probe with `IS NOT DISTINCT FROM` so NULL/NULL compares as equal.
- `ORDER BY col DESC` puts NULLs FIRST (ASC puts them last), so a "keep the newest row" dedup written `ORDER BY updated_at DESC` picks the row whose timestamp is NULL. ORM `timestamps()` helpers typically create `created_at`/`updated_at` as nullable, so the exposure is routine rather than exotic. Pin the order (`ORDER BY updated_at DESC NULLS LAST, id DESC`) or make the column `NOT NULL`. MySQL's DESC default is the opposite (NULLS LAST), so a query ported between the two silently changes which row survives.
- Revoke default public schema access: `REVOKE ALL ON SCHEMA public FROM public`
- Derive every attribute at its own grain. A property of the parent (a session, a day, an order) computed from one child row lands on every child and is legitimately partial for most of them, so the aggregate disagrees with itself depending on which child is read. Put parent-scoped facts in a table keyed at the parent grain, populate them from the child the parent designates, and prefer a boundary observation (the last event's timestamp) over a count threshold.


## Migration Safety

**Core rules:**
- Every schema change is a migration. No ad-hoc DDL in production.
- Migrations are immutable once deployed; never edit a migration that has run in any shared environment.
- Schema migrations and data migrations are separate files. Schema changes are fast and transactional; data backfills are slow and may need batching. Exception: when one transaction is what closes a rolling-deploy null window, do not split reflexively; see the `ADD COLUMN` lock note under Dangerous operations for the table-size disposition.
- Forward-only in production. Rollback = a new forward migration that reverses the change.
- A re-run guard that checks one object (`IF EXISTS`-style early return on the main table) is a valid proxy for "everything already applied" **only** when the entire migration body runs in one transaction. PostgreSQL rolls `CREATE TABLE` / `CREATE TYPE` / `CREATE INDEX` (non-concurrent) / `CREATE FUNCTION` / `CREATE TRIGGER` / `ALTER TABLE` back together, so table-exists implies the rest committed. Any statement that cannot run inside a transaction (`CREATE INDEX CONCURRENTLY`, `ALTER TYPE ... ADD VALUE` on older versions, `VACUUM`) sits outside that guarantee, and the guard then skips it on re-run and ships a partial schema. Confirm every DDL object is inside the one transaction before relying on the guard.

**Expand-contract pattern** for zero-downtime renames and removals:

1. **Expand**: add the new column/table, backfill data, update writes to populate both old and new
2. **Migrate**: switch reads to the new column/table, verify in production
3. **Contract**: remove the old column/table in a later deploy

Never rename or remove a column in a single migration; callers reading the old name will break between deploy and code rollout.

The transitional window covers every layer a client reads, not just the column. A migration can be flawlessly rolling-deploy-safe on the write side while the same release drops the field from the API response, and a bundle loaded before the deploy then reads `undefined`: a render-time crash, not a graceful absence. Enumerate the field's treatment per layer (column, response payload, each client) and keep the response emitting it until the same later release that drops the column. "The client change ships alongside" addresses new bundles, not the ones already running.

**Dangerous operations:**
- `NOT NULL` without a `DEFAULT` on an existing table locks and rewrites every row. Add the column nullable first, backfill, then add the constraint.
- `CREATE INDEX` (without `CONCURRENTLY`) locks writes for the duration. Always use `CONCURRENTLY`, which cannot run inside a transaction block; keep it in its own migration.
- `ADD COLUMN ... NULL` with no default is metadata-only and fast, but it takes `ACCESS EXCLUSIVE` and that lock is held until the enclosing **transaction** commits, not until the `ALTER` returns. A migration that adds the column and then backfills every row in the same transaction blocks all readers and writers for the backfill's duration. Do not reflexively split it: the single-transaction ordering (`ADD` nullable -> backfill -> `SET DEFAULT`) is itself the fix for the rolling-deploy window where an old release inserts `NULL` before the default exists. The disposition is table size, not a rule: on a small table accept the sub-second hold and state the row count; on a large one use expand-contract (deploy the column with a constant `DEFAULT` first, then a separate chunked backfill outside a transaction).
- A dedup pass preceding a **partial** unique index must carry the index's own predicate. `CREATE UNIQUE INDEX ... WHERE <pred>` constrains only the rows matching `<pred>`, but a dedup that ranks over the whole table collapses each key to a single row and hard-deletes `<pred>`-failing rows the index would have allowed: silent data loss on a forward-only migration. Put `<pred>` inside the ranked subquery, and compare the delete's row count against a `SELECT count(*) ... WHERE NOT <pred>` before committing.
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

- **In-place atomic update** when the edit is expressible as SQL: `UPDATE t SET col = jsonb_set(col, '{path}', :value) WHERE ...`, or `UPDATE t SET tags = array_append(tags, :tag) WHERE ...`. No read-modify-write window.
- **Row-level lock during the loop:** wrap each iteration in a transaction, `SELECT ... WHERE id = ? FOR UPDATE`, then mutate and write. Cheaper to author, accepts more lock contention.
- **Compare-and-swap retry:** include the original snapshot in `WHERE col = :original_value`, check the affected-row count; on 0, re-read and retry. Holds under contention, requires explicit retry-loop handling.

Default chunked decode-encode loops are only safe during a maintenance window with writes blocked. ORM "chunkById + load + mutate + save" patterns hit this same trap.

**A SQL backfill claiming parity with an application normalizer usually differs on a character class.** One-argument `btrim(x)` trims spaces only, while PHP's `trim()` and Python's `.strip()` trim the whole ASCII whitespace set, so a value carrying a tab folds out of vocabulary in SQL, and on a value-dropping migration that is one-way data loss. Pass the character set explicitly (`btrim(x, E' \t\n\r\x0B')`, which mirrors PHP's default) and apply it to the blank guard as well as the comparison. Whenever a query re-implements an application normalizer, enumerate every class each side treats as insignificant (whitespace, case folding, Unicode normalization, trailing punctuation) and execute both over the same inputs, loading the committed implementation verbatim rather than retyping it.

**Rollback fidelity is executable.** Reviewers compare the up and down SQL as strings and agree they look symmetric, which misses a renamed index, a dropped partial predicate, or an operator-class difference. Hold the migration out and build the baseline, restore and apply it, roll back one step, then diff the catalog's normalized output (`pg_indexes.indexdef`, `pg_get_constraintdef(oid)`); an empty diff is the answer, and no amount of reading is. Run it on anything that rebuilds a unique or partial index, or re-keys an index in place.
