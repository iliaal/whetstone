## Concurrency Patterns

**UPSERT** -- atomic insert-or-update, avoids race conditions:
```sql
INSERT INTO settings (user_id, key, value)
VALUES (123, 'theme', 'dark')
ON CONFLICT (user_id, key)
DO UPDATE SET value = EXCLUDED.value, updated_at = now()
RETURNING *;
```

**Deadlock prevention** -- acquire locks in deterministic order:
```sql
SELECT * FROM accounts WHERE id IN (1, 2) ORDER BY id FOR UPDATE;
-- Or collapse into single atomic statement:
UPDATE accounts SET balance = balance + CASE id
  WHEN 1 THEN -100 WHEN 2 THEN 100 END
WHERE id IN (1, 2);
```

**N+1 elimination** -- batch with array parameter instead of per-row queries:
```sql
SELECT * FROM orders WHERE user_id = ANY($1::bigint[]);
```

**Batch inserts** -- multi-row VALUES (up to ~1000 per batch), or `COPY` for bulk loading:
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
