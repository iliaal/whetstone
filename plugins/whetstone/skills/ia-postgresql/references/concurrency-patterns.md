## Concurrency Patterns

**UPSERT**: atomic insert-or-update, avoids race conditions:
```sql
INSERT INTO settings (user_id, key, value)
VALUES (123, 'theme', 'dark')
ON CONFLICT (user_id, key)
DO UPDATE SET value = EXCLUDED.value, updated_at = now()
RETURNING *;
```

**Deadlock prevention**: acquire locks in deterministic order:
```sql
SELECT * FROM accounts WHERE id IN (1, 2) ORDER BY id FOR UPDATE;
-- Or collapse into single atomic statement:
UPDATE accounts SET balance = balance + CASE id
  WHEN 1 THEN -100 WHEN 2 THEN 100 END
WHERE id IN (1, 2);
```

**Foreign-key row locks cut both ways.** Inserting a child row takes `FOR KEY SHARE` on the parent row it references, and the row-lock conflict table gives `FOR KEY SHARE` exactly one conflicting mode: `FOR UPDATE`. Two opposite consequences follow, and only the order distinguishes them:

- Lock the parent, *then* insert the child: concurrent creators serialize, because the second transaction's `FOR UPDATE` waits on the first transaction's `KEY SHARE`.
- Insert the child, *then* lock the parent: two concurrent runs of that one path deadlock. Each already holds `KEY SHARE` from its own insert and each asks to upgrade to `FOR UPDATE`, so Postgres aborts one with `deadlock detected` / `while locking tuple ... in relation "<parent>"` and the caller gets a 500.

`FOR SHARE` and `FOR NO KEY UPDATE` do not conflict with `KEY SHARE`, so neither serializes the child insert; a shared-lock "fix" is a no-op. Detector: for every parent-row `FOR UPDATE`, check whether the same transaction already inserted a row referencing that parent; if it did, the path deadlocks against itself under concurrency. The late lock is often deliberate (keeping a row lock off an outbound network call). Where it is, keep it where it sits and swap it for a transaction-scoped advisory lock on the parent key: it orders the same writers, takes nothing on the parent tuple, and so cannot participate in the upgrade:

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
