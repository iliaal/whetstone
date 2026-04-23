# Database Review Triggers (grep-first)

Load this reference at the start of any migration or data-handling review. Run these greps before reading the diff end-to-end — each corresponds to a known class of silent data corruption caught in production review.

## JSON-column migration clobber

```
grep -n 'json_decode.*->metadata\|json_decode.*->data\|json_decode.*->attributes' <migration files>
```

If you find `chunkById + json_decode + mutate + json_encode + update` on a jsonb column without `lockForUpdate()` or a maintenance-window comment, flag as high-risk. The SELECT→UPDATE window is milliseconds; concurrent user writes are silently overwritten by the migration's stale snapshot. Correct alternatives: in-place `DB::raw("jsonb_set(metadata, '{path}', ...)")`, or `lockForUpdate()` inside the chunk, or compare-and-swap with the original JSON in the WHERE clause.

## Query-builder update skipping observers/audit

```
grep -rn '::query()->.*->update(' <touched model paths>
grep -rn '#\[ObservedBy' app/Models
grep -rn 'IsAuditable\|Auditable' app/Models
```

`Model::query()->where(...)->update([...])` does NOT fire Eloquent model events. Any observer, OwenIt Auditable trait subscribe, or model-boot `static::saving/updating` callback is silently skipped. If the target model is auditable or has observers, the migration loses audit rows and side effects without any visible signal. Flag and recommend `DB::transaction(fn() => $row = Model::whereKey($id)->lockForUpdate()->first(); ...; $row->save());` unless the bypass is intentional and commented.

## Column rename missed JSON-embedded copies

```
grep -rn "'<old-value>'\|\"<old-value>\"" <migration files> database/migrations/
```

If a column-level rename also needs to update the same semantic value embedded in JSON columns in other tables (requirement payloads, config snapshots, settings trees), the migration is incomplete. Check past rename migrations in the same repo — they're the best index of where the value actually lives.

## DynamoDB FilterExpression + Limit pagination

```
grep -rn 'FilterExpression.*Limit\|Limit.*FilterExpression' <repository paths>
```

DynamoDB applies FilterExpression AFTER Limit. A paginated scan with a filter returns *underfilled* pages — up to `Limit` items are fetched, then the filter rejects some, so you get 0..Limit rows even when more match. Callers expecting exact-page semantics break. Fix: fetch in a loop until either the result set is filled or the scan cursor (`LastEvaluatedKey`) is null.

## Full-attribute replace against a stale snapshot

Patterns like `UPDATE ... SET attributes = :attributes WHERE id = :id` where `:attributes` is built from a prior SELECT's snapshot silently drop sibling attributes added by concurrent writes. Read-modify-write with `lockForUpdate()` (Postgres) or conditional update with current-value WHERE clause (DynamoDB, Postgres) are the fixes.

## Enum case added without mirroring in a paired enum

When a migration or code change adds a new case to enum A, grep for `Rule::enum(A::class)` AND `A::class` cast references, AND grep for any sibling enum with overlapping cases. Paired enums nothing in the type system protects — a validator accepting the new case and a cast rejecting it on read produces post-deploy write-then-read crashes.
