---
name: ia-postgresql
class: language
description: >-
  PostgreSQL schema design, query optimization, indexing, and administration.
  Use when working with PostgreSQL, JSONB, partitioning, RLS, CTEs, window
  functions, or EXPLAIN ANALYZE.
---

# PostgreSQL

## Working rules

- Preserve raw bytes as bytes when fidelity matters; choose parsed types separately for querying.
- Treat deployed migrations as immutable and account for old and new application versions during rollout.
- Check lock duration and transaction scope; protect read-modify-write paths against concurrent updates.
- Match index predicates and NULL semantics to every writer and migration query.
- Measure query changes with representative data and actual plans; verify invariants as database outcomes.

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
| Raw bytes (verbatim payload) | `BYTEA` | `JSONB`, `TEXT` (both re-encode) |

A spec that says "log the raw response" is asking for byte fidelity, and no text type provides it. `JSONB` reparses: it drops insignificant whitespace, sorts object keys, keeps only the last of duplicate keys, and rewrites numbers out of exponent notation (`1e0` -> `1`; trailing zeros in `1.00` do survive, so "all numeric forms collapse" overstates it). A non-JSON body cannot be stored at all and usually lands as `NULL`. `TEXT` rejects a NUL byte and any sequence invalid in the database encoding, so a binary or mis-encoded body errors instead of storing. Persist the bytes in `BYTEA` with the content type beside them, and add a parsed `JSONB` column separately when queries need one. Reading the column type as proof the body is kept is the review error.


## Verify

Run `EXPLAIN (ANALYZE, BUFFERS)` on changed queries with representative data. Investigate unexpected sequential scans and compare actual costs; accept a sequential scan when reading much of a table is cheaper than using an index. Confirm no unindexed FK columns before declaring done.

## Task-specific references

Read the relevant reference before implementing or reviewing the matching behavior:

- For table design, constraints, schema changes, or backfills: [schema-and-migrations.md](./references/schema-and-migrations.md).
- For indexes, query plans, JSONB, pagination, or query anti-patterns: [query-and-index-patterns.md](./references/query-and-index-patterns.md).
- For RLS, transaction boundaries, locks, partitioning, pooling, or operational features: [security-and-operations.md](./references/security-and-operations.md).

Existing specialized references, when the corresponding topic applies:

- [operations.md](./references/operations.md).
- [concurrency-patterns.md](./references/concurrency-patterns.md).
- [full-text-search.md](./references/full-text-search.md).
- [performance-patterns.md](./references/performance-patterns.md).
