# Database & Production

## Database

ORM: **Drizzle** (SQL-like, lightweight) or **Prisma** (schema-first, migrations built-in)

Connection pooling: `new Pool({ max: 20, idleTimeoutMillis: 30000, connectionTimeoutMillis: 2000 })`

Transactions: `BEGIN` → ops → `COMMIT` / catch → `ROLLBACK` / finally → `client.release()`

Index strategies:
```sql
CREATE INDEX idx_col ON t(col);                            -- equality
CREATE INDEX idx_multi ON t(col1, col2);                   -- composite
CREATE INDEX idx_partial ON t(col) WHERE status = 'active'; -- filtered
CREATE INDEX idx_cover ON t(col) INCLUDE (name);            -- covering
```

Always `EXPLAIN ANALYZE` slow queries. Watch for sequential scans on large tables.

**Migrations:**
- Separate schema and data migrations -- data backfills in their own migration file
- Renames/removals use expand-contract: add new column → backfill → switch reads → drop old (see `ia-postgresql` skill for the full pattern)
- Never edit a migration that has already run in a shared environment
- Kysely: always type migrations as `Kysely<any>`, not your app's typed DB interface -- migrations are frozen in time and the schema will evolve past them
- Drizzle/Prisma: keep migration SQL files under version control, review generated SQL before applying

## Production

- **Docker**: multi-stage build -- `node:20-alpine` builder + prod image with `npm ci --omit=dev`
- **Process**: PM2 cluster mode (`instances: 'max'`) or container orchestration
- **Shutdown**: SIGTERM → stop accepting connections → drain in-flight → close DB pool
- **Logging**: Pino (structured JSON), not console.log
- **Health**: `GET /health` returning `{ status: 'ok' }`
- **Compression**: gzip/brotli via middleware
