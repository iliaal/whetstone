# Laravel Pitfalls — Deep Reference

Extended mechanics and alternative patterns for the Common Pitfalls section of SKILL.md.

## `DB::afterCommit`: closing the post-commit-failure half

`DB::afterCommit($closure)` prevents external work (S3, search index, third-party webhook) from running when the transaction rolls back. It does NOT retry the external op when it fails after commit — the closure runs once, exceptions bubble out of the response cycle, the operation drops, and the DB row now advertises a state the external system doesn't reflect.

Closing patterns:

- **(a) Queued job with retries — the general-purpose default.** Dispatch a queued job with `tries` + exponential backoff + a `failed(Throwable $e)` handler that reverts the DB precondition the job was supposed to make true. Queue retry semantics already model the transient/permanent split.
- **(b) External-op-first, then DB.** Perform the external mutation before the DB write, so a DB failure leaves only harmless external residue. Only valid when the op is idempotent on the destination key: `Storage::copy` retries cleanly; `Storage::move` fails on the second attempt because the source is gone.
- **(c) Reconciler command.** A scheduled command walks rows with stuck "in-flight" flags and re-drives or reverts them. Reach for this when jobs can be lost entirely (queue driver failure) or the writes originate from multiple code paths.

## Observer-desync mechanics

When an observer fires mid-flow (e.g. `Document::deleted` → `$verifiable->update([...])`) and mutates a model the caller is also mutating, the two instances share no state — Eloquent dirty-tracking compares in-memory current vs in-memory original, never the DB. The caller's later `save()` only writes columns it changed, so:

- a column the observer cleared stays cleared on disk, and
- a column the caller set back to its in-memory original is seen as not-dirty and never re-written.

`DB::transaction` doesn't help — this is in-memory state, not isolation. Fixes: `$model->refresh()` in the caller after the triggering event and before its later `save()`, or run the triggering write under `Model::withoutEvents(...)` when the caller owns that column's semantics for the flow.

## jsonb read-modify-write race

In `chunkById + json_decode + mutate + json_encode + update`, the window between the SELECT populating `$row->metadata` and the per-row UPDATE is milliseconds — any user save landing in that window is silently overwritten by the migration's stale snapshot. In-place `DB::raw("jsonb_set(metadata, '{path}', ...)")` avoids the read entirely for shallow edits; `lockForUpdate()` inside the chunk serializes with concurrent writers when arbitrary PHP logic is needed. The default decode/encode pattern is only safe during a maintenance window with writes blocked.

## `$withinTransaction` savepoint mechanics (Postgres)

Migrations default to `public $withinTransaction = true` — on Postgres/SQLite all of `up()` runs in one outer transaction. A per-row `DB::transaction()` loop inside a data backfill therefore creates nested savepoints, not independent commits: each inner "commit" merely releases a savepoint, nothing is durable until `up()` returns, and row locks accumulate for the whole run. One mid-loop failure rolls back every prior row. MySQL auto-commits DDL, so the flag is a no-op there.
