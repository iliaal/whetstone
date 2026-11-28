# PostgreSQL Operations

## Performance Tuning

Key `postgresql.conf` parameters (adjust for available RAM):
- `shared_buffers` = 25% of RAM
- `effective_cache_size` = 75% of RAM
- `work_mem` = RAM / max_connections / 4 (start 4-16MB)
- `maintenance_work_mem` = 256MB-1GB
- `random_page_cost` = 1.1 for SSD (default 4.0 is for HDD)

## Maintenance & Monitoring

- `pg_stat_statements` extension: find slow queries by total time, not just duration
- `pg_stat_user_tables`: check `n_dead_tup` for vacuum needs, `last_autovacuum` timestamps
- Cache hit ratio (should be > 99%): `SELECT sum(heap_blks_hit) / sum(heap_blks_hit + heap_blks_read) FROM pg_statio_user_tables`

**Autovacuum tuning for hot tables:**
```sql
ALTER TABLE orders SET (
  autovacuum_vacuum_scale_factor = 0.05,   -- default 0.2
  autovacuum_analyze_scale_factor = 0.02
);
```

**XID wraparound prevention**: monitor transaction ID age (emergency shutdown at 2B):
```sql
SELECT datname, age(datfrozenxid),
  round(100.0 * age(datfrozenxid) / 2147483648, 2) AS pct_to_wraparound
FROM pg_database ORDER BY age DESC;
```

Set `idle_in_transaction_session_timeout = '30s'` and `statement_timeout = '30s'` to prevent long-running transactions from blocking vacuum.

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

-- Zero-scan candidates, excluding uniqueness and exclusion indexes
SELECT s.schemaname, s.relname, s.indexrelname, s.idx_scan
FROM pg_stat_user_indexes AS s
JOIN pg_index AS i ON i.indexrelid = s.indexrelid
WHERE s.idx_scan = 0 AND i.indisvalid AND NOT i.indisunique AND NOT i.indisexclusion
ORDER BY pg_relation_size(s.indexrelid) DESC;
```

Before proposing removal, verify statistics cover a full representative business cycle on every node that serves the workload. Check database and per-index statistics resets, restarts, and access patterns on replicas. Exclude indexes required by constraints, foreign-key lookups, or other workload plans. A zero scan count is a candidate signal alone.

## WAL (Write-Ahead Logging)

Changes write to `pg_wal/` before data files. Checkpoints flush dirty pages to disk. If "checkpoints occurring too frequently" appears in logs, increase `max_wal_size`. Never disable `fsync`.

Key config:
- `checkpoint_timeout` = 5min (default, usually fine)
- `checkpoint_completion_target` = 0.9 (spread I/O)
- `max_wal_size`: increase if checkpoint warnings appear

Monitor WAL disk usage:
```sql
SELECT count(*) AS files, pg_size_pretty(sum(size)) AS total
FROM pg_ls_waldir();
```

## Replication

Streaming replication sends WAL to hot standbys (read-only). Replication slots guarantee WAL retention but can exhaust disk if standby goes offline; use `max_slot_wal_keep_size` to cap.

Monitor lag:
```sql
SELECT application_name,
  pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn)/1024/1024 AS lag_mb
FROM pg_stat_replication;
```

Monitor slot lag (prevent disk exhaustion):
```sql
SELECT slot_name,
  pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)/1024/1024 AS mb_behind
FROM pg_replication_slots;
```

Synchronous commit levels: `off` (lose ~600ms on crash) to `remote_apply` (read-your-writes guarantee). Provision N+1 standbys for N required confirmations.

For manual failover, fence the old primary from all writes before promotion, including after a restart or network recovery. Use the standby's `SELECT pg_promote()` (PG12+) and verify promotion completed and only the promoted node can accept writes before sending traffic there. Keep the old primary fenced until it rejoins as a standby. Use `pg_rewind` if its prerequisites are met, or rebuild it from a new base backup. Verify equivalent fencing in managed failover. See [PostgreSQL failover](https://www.postgresql.org/docs/18/warm-standby-failover.html).

## Backup & Recovery

| Method | Tool | Speed | Portability | Use When |
|--------|------|-------|-------------|----------|
| Logical | `pg_dump` | Slow | Cross-version | Small DBs, selective restore |
| Physical | `pg_basebackup` | Fast | Same major version | Large DBs, full cluster |
| PITR | Base backup + WAL archive | Fast | Same major version | Production point-in-time restore |

Without WAL replay, recovery is limited to the latest usable backup. With continuous archiving, the recoverable point depends on the latest durable WAL and any gap in the archive.

Configure production WAL archiving with pgBackRest, Barman, or WAL-G. For a pgBackRest cluster configured as stanza `main` with a backup repository:

```conf
archive_mode = on
archive_command = 'pgbackrest --stanza=main archive-push %p'
```

Use `wal_level = replica` or higher. Restart to enable `archive_mode`, initialize the stanza, then run `pgbackrest --stanza=main check` as the PostgreSQL service user. See the [pgBackRest archiving procedure](https://pgbackrest.org/user-guide.html).

A custom archive command must durably publish each complete segment atomically without replacing an existing archive. On retry, return success for an identical segment already confirmed durable. Preserve the stored segment, fail, and alert on different contents. Test interrupted archiving, duplicate and conflicting retries, and restoration through the archived WAL. See [PostgreSQL continuous archiving](https://www.postgresql.org/docs/18/continuous-archiving.html#BACKUP-ARCHIVING-WAL).

Verify archiving health:
```sql
SELECT last_archived_wal, last_archived_time, failed_count
FROM pg_stat_archiver;
```

Test recovery regularly by restoring a base backup and replaying archived WAL to the intended point.
