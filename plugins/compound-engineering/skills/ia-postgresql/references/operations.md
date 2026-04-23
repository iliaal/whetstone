# PostgreSQL Operations

## Performance Tuning

Key `postgresql.conf` parameters (adjust for available RAM):
- `shared_buffers` = 25% of RAM
- `effective_cache_size` = 75% of RAM
- `work_mem` = RAM / max_connections / 4 (start 4-16MB)
- `maintenance_work_mem` = 256MB-1GB
- `random_page_cost` = 1.1 for SSD (default 4.0 is for HDD)

## Maintenance & Monitoring

- `pg_stat_statements` extension -- find slow queries by total time, not just duration
- `pg_stat_user_tables` -- check `n_dead_tup` for vacuum needs, `last_autovacuum` timestamps
- Cache hit ratio (should be > 99%): `SELECT sum(heap_blks_hit) / sum(heap_blks_hit + heap_blks_read) FROM pg_statio_user_tables`

**Autovacuum tuning for hot tables:**
```sql
ALTER TABLE orders SET (
  autovacuum_vacuum_scale_factor = 0.05,   -- default 0.2
  autovacuum_analyze_scale_factor = 0.02
);
```

**XID wraparound prevention** -- monitor transaction ID age (emergency shutdown at 2B):
```sql
SELECT datname, age(datfrozenxid),
  round(100.0 * age(datfrozenxid) / 2147483648, 2) AS pct_to_wraparound
FROM pg_database ORDER BY age DESC;
```

Set `idle_in_transaction_session_timeout = '30s'` and `statement_timeout = '30s'` to prevent long-running transactions from blocking vacuum.

## WAL (Write-Ahead Logging)

Changes write to `pg_wal/` before data files. Checkpoints flush dirty pages to disk. If "checkpoints occurring too frequently" appears in logs, increase `max_wal_size`. Never disable `fsync`.

Key config:
- `checkpoint_timeout` = 5min (default, usually fine)
- `checkpoint_completion_target` = 0.9 (spread I/O)
- `max_wal_size` -- increase if checkpoint warnings appear

Monitor WAL disk usage:
```sql
SELECT count(*) AS files, pg_size_pretty(sum(size)) AS total
FROM pg_ls_waldir();
```

## Replication

Streaming replication sends WAL to hot standbys (read-only). Replication slots guarantee WAL retention but can exhaust disk if standby goes offline -- use `max_slot_wal_keep_size` to cap.

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

Failover: `SELECT pg_promote()` (PG12+). Use `pg_rewind` to resync old primary as new standby without full rebuild (requires `wal_log_hints=on` or data checksums).

## Backup & Recovery

| Method | Tool | Speed | Portability | Use When |
|--------|------|-------|-------------|----------|
| Logical | `pg_dump` | Slow | Cross-version | Small DBs, selective restore |
| Physical | `pg_basebackup` | Fast | Same major version | Large DBs, full cluster |
| PITR | Base backup + WAL archive | Fast | Same major version | Production (minutes RPO) |

Without PITR, RPO = backup interval (often 24h). With continuous WAL archiving, RPO drops to minutes.

Enable WAL archiving:
```
archive_mode = on
archive_command = 'test ! -f /archive/%f && cp %p /archive/%f'
```

Verify archiving health:
```sql
SELECT last_archived_wal, last_archived_time, failed_count
FROM pg_stat_archiver;
```

For production, use pgBackRest, Barman, or WAL-G over raw `pg_basebackup`. Test recovery regularly -- backups are useless until you've successfully restored from one.
