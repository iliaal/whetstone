## Concurrency Patterns

**UPSERT**: atomic insert-or-update, avoids race conditions:
```sql
INSERT INTO settings (user_id, key, value)
VALUES (123, 'theme', 'dark')
ON CONFLICT (user_id, key)
DO UPDATE SET value = EXCLUDED.value, updated_at = now()
RETURNING *;
```

The conflict target must restate a partial or expression unique index: `ON CONFLICT ((coalesce(a, 'x')), b) WHERE pred`. A bare column list matches only a plain unique index or constraint, which is why ORM upserts that emit a column list fail against these indexes with `no unique or exclusion constraint matching the ON CONFLICT specification`.

**Replayed or reordered events:** when the upsert consumes events that can be redelivered or arrive out of order (CDC, webhooks, queue consumers, backfills), carry a source-owned version that increases per key and guard the update: `ON CONFLICT (id) DO UPDATE SET status = EXCLUDED.status, version = EXCLUDED.version WHERE orders.version < EXCLUDED.version`. Without the guard, a late older event overwrites newer state. The guard fits only events that carry the full state of every column they set. For delta events (an increment, an appended item), apply an event only when `version = current + 1`, park later versions until the gap fills, and reconcile from the source of truth when a gap outlives its window; a `<` guard would apply v5 and then skip a late v4 as stale, losing its change. Arrival time, `now()`, and random event IDs cannot order events. A skipped stale event returns zero rows from `RETURNING`, so treat an empty result as "already newer", not as a failure. Reject or quarantine two different payloads at the same key and version instead of letting arrival order pick one; the guard cannot tell them apart, so store a payload hash beside `version` and compare it in a separate check when the same version can carry different data.

**Deadlock prevention:** Acquire row locks in a consistent order by an immutable key across all competing paths. A single atomic update can avoid a read-modify-write race on one row. A multi-row update's plan determines row-lock acquisition order. Lock the target rows explicitly before updating them in the same transaction.

```sql
BEGIN;
SELECT id FROM accounts WHERE id IN (1, 2) ORDER BY id FOR UPDATE;
-- Continue only if both account IDs were returned.
UPDATE accounts SET balance = balance + CASE id
  WHEN 1 THEN -100 WHEN 2 THEN 100 END
WHERE id IN (1, 2);
COMMIT;
```

**Transaction retries:** On SQLSTATE `40001`, roll back the top-level transaction. Retry the [complete transaction](https://www.postgresql.org/docs/18/mvcc-serialization-failure-handling.html), including every read and the application decisions that choose statements and values. Retrying only the failed statement can reuse stale inputs; a savepoint retry at `REPEATABLE READ` or `SERIALIZABLE` retains the transaction snapshot. Bound retries with backoff and jitter. Use the same retry boundary for `40P01` deadlocks. Correct inconsistent lock order. Keep non-idempotent external effects outside replayable transaction work. A connection lost during `COMMIT` leaves the outcome unknown, since the transaction may have committed before the reply was lost, so exclude connection errors (SQLSTATE class `08`, driver connection errors) from the retry predicate, even when a helper marks them retryable, unless the transaction is idempotent or its committed state is checked first (for example through an idempotency key).

**Foreign-key checks take `FOR KEY SHARE` on the referenced parent row.** When checks run during child insertion, order matters if the same transaction also takes `FOR UPDATE` on the parent.

- Take `FOR UPDATE` on the parent first. It blocks other parent lockers and child inserts that need `KEY SHARE` on that same row.
- Insert the child first, then take `FOR UPDATE`. Two sessions can each hold `KEY SHARE` and deadlock on the upgrade.

`FOR SHARE` and `FOR NO KEY UPDATE` both allow child inserts that only take `KEY SHARE`. `FOR NO KEY UPDATE` conflicts with itself and can serialize cooperating paths that all take that lock. When the critical section must start after a child insert and all writers cooperate, another option is a transaction-scoped advisory lock on the parent key. It leaves the parent tuple lock unchanged. Use the same key and acquire it before reading or writing the protected state. See the [row-lock conflict matrix](https://www.postgresql.org/docs/18/explicit-locking.html#LOCKING-ROWS).

```sql
SELECT pg_advisory_xact_lock(hashtextextended('organization:' || $1, 0));
```

**A row lock does not order reads.** It serializes the writes; it does not make a value read before the lock current. Under READ COMMITTED a `SELECT ... FOR UPDATE` waits for the concurrent writer and returns *that* transaction's updated row, so the re-read under the lock is what supplies the fresh value:

```sql
BEGIN;
-- steering input read INSIDE the lock, from the locked row
SELECT status, plan_id FROM accounts WHERE id = $1 FOR UPDATE;
-- ... work computed from the values just read
COMMIT;
```

The failing shape resolves the steering value above the lock (often above `BEGIN`, in application code) and passes it into the locked block. The lock is genuinely correct and the race survives: both transactions compute from the same pre-lock snapshot, and whichever the lock admits second commits work derived from the stale one. Clearing a lock-based fix means tracing every value the locked block acts on back to its read site and confirming it sits inside the lock, not confirming that the lock statement comes first.

**N+1 elimination**: batch with array parameter instead of per-row queries:
```sql
SELECT * FROM orders WHERE user_id = ANY($1::bigint[]);
```

**Batch inserts**: multi-row VALUES (up to ~1000 per batch), or `COPY` for bulk loading:
```sql
INSERT INTO events (user_id, action) VALUES
  (1, 'click'), (1, 'view'), (2, 'click');
```

**Queue processing:**
```sql
UPDATE jobs SET status = 'processing'
WHERE id = (
  SELECT id FROM jobs WHERE status = 'pending'
  ORDER BY created_at LIMIT 1
  FOR UPDATE SKIP LOCKED
) RETURNING *;
```
