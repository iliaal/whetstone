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

## Eloquent pitfalls

### CastsAttributes get() cache merges back through save()

A custom `CastsAttributes` whose `get()` returns an object is cached and merged BACK through `set()` on the next `save()`. `getClassCastableAttributeValue()` parks any object return in `$classCastCache` (a `BackedEnum` is an object, so enums qualify), and `Model::save()` opens with `mergeAttributesFromCachedCasts()`. So the tolerant `tryFrom($v) ?? default()` read idiom -- written precisely so an unrecognised stored value degrades during a rolling deploy instead of throwing -- destroys that value: read the attribute, save the model for any unrelated reason, and the unknown string is rewritten as the default. It degrades on read and corrupts on write, in exactly the scenario it exists for. Fix: `public bool $withoutObjectCaching = true;` on the cast. Anything whose job is preserving the stored value -- an audit recorder, a pre-delete snapshot -- must read `getRawOriginal()`, or it records the normalised fallback and the real value is unrecoverable.

### Builder::value()/pluck() cast vs DB::table raw column

`Builder::value()` and `pluck()` return the CAST attribute; `DB::table(...)->value()` returns the raw column. `value()` is `first([$column])` followed by `$result->{$column}`, so the value goes through `getAttribute()` and the cast applies. A guard like `is_string($v) ? Enum::tryFrom($v) : null` therefore returns `null` forever -- no error, no exception, PHPStan clean (`value()` is typed `mixed`, so the narrowing is legal), and green tests, because whatever the guard was meant to reject is now accepted. Accept both shapes: `$v instanceof Enum ? $v : (is_string($v) ? Enum::tryFrom($v) : null)`. The mechanism also fires in reverse -- adding a `$casts` entry for an existing column silently disables every such guard reading it, with no change at any call site for a diff-scoped review to see. When a diff adds a cast, grep every `->value('<column>')` / `->pluck('<column>')` whose result meets `is_string`, `is_int`, a `match`, or a bare `===` against a literal.

### enforceMorphMap() throws only from audit-gated code paths

With `Relation::enforceMorphMap()`, a model missing from the map throws `ClassMorphViolationException` from `getMorphClass()` -- and almost nothing calls `getMorphClass()` on an ordinary `create()` except the audit layer, which is usually config-gated off under test. So a new model with no map entry passes the entire suite, including tests that create it, and 500s on the first write in an environment where auditing is on. The throw fires inside whatever transaction the write is in, so one unmapped child model rolls back the parent record, its links and any status transition -- the whole request, not just the audit. Add the map entry in the same commit as the model; with `enforceMorphMap` it is part of the class working at all, and overriding an audit-label method is a separate call site that does not substitute. A green suite is not evidence here: check whether the config flag gating the consumer is false under test.

## Queue pitfalls

### ShouldBeUnique silently discards, does not guarantee

`ShouldBeUnique` interface to prevent duplicate processing -- it is a de-duplication hint, not an at-least-once guarantee. When the lock is already held the dispatch is **silently discarded**: no job queued, no exception, no log line, and `dispatch()` returns normally. Where the skip is user-visible (a re-clicked "regenerate report" that produces nothing), check the lock before dispatching and surface the state. A `Illuminate\Queue\Events\UniqueJobSkipped` event exists on the `13.x` branch but had not landed in a tagged release as of 13.24 -- confirm it is in the installed version before listening for it.

### WithoutOverlapping lock key includes the job class

`WithoutOverlapping` folds the job's class name into the lock key, so two job classes sharing a key do NOT serialize against each other. `getLockKey()` returns `prefix.get_class($job).':'.$key` unless `->shared()` was called, and `->shared()` is per-middleware-instance -- adding it to only the new job is a no-op, and the remedy therefore has to touch the other job's file. A test asserting `$middleware[0]->key` passes either way, since the public property is equal on both jobs and unaffected by `->shared()`; assert `getLockKey($job)` across both instances, or assert real contention. Changing an already-deployed job's key also opens a rolling-deploy window where old and new workers hold different locks. Before trusting the guarantee at all, check whether the other writer is a job: a synchronous in-request writer takes no queue middleware, so no lock setting can serialize against it.

### dontRelease() without expireAfter strands the lock

`WithoutOverlapping()->dontRelease()` with no `->expireAfter()` strands the lock on a hard kill. `expiresAfter` defaults to `0`, which builds a cache lock with no TTL, and the lock is released only in the middleware's `finally` -- SIGKILL, the OOM killer, or a node loss skips it. From then on every job for that key hits the lock-held branch and, because `dontRelease()` set `releaseAfter = null`, falls through both branches and is silently discarded: not run, not retried, not failed, no error surfaced. Any reconciliation command that re-dispatches is discarded too, so the backstop silently no-ops. The knobs are orthogonal -- `dontRelease` = no pile-up, `expireAfter` = self-heal -- and defending one does not address the other. Set a TTL safely longer than the job's worst-case runtime and keep `dontRelease()`.

### Context does not bleed between queued jobs

`Context` cannot bleed between queued jobs -- it is flushed and rehydrated from each job's own dispatch payload before `handle()` runs. `ContextServiceProvider` dehydrates the dispatcher's context into the payload and calls `Context::hydrate()` on `JobProcessing`; `Repository::hydrate()` runs `flush()` first, every time, including when the payload is `null`. So "this job sets Context and never clears it, the next job inherits it" is not a bug. The genuine bleed surface is Octane/Swoole/RoadRunner on the HTTP path, where the repository is an app singleton and a middleware that sets Context for only some requests leaves it set for a later request that does not overwrite it -- a non-issue under PHP-FPM. Within one job Context is shared for the duration, so a handler serving multiple audiences must re-set it per audience.

## Concurrency pitfalls

### `Concurrency::run()` leaks hidden Context into the child process environment

The process driver passes `'__LARAVEL_CONTEXT' => json_encode(Context::dehydrate())` as an env var to every pooled child process. `dehydrate()` does keep hidden values under a separate `hidden` key (`['data' => ..., 'hidden' => ...]`), but `ProcessDriver` JSON-encodes the whole array into one env var with no filtering, so hidden values travel with the visible ones regardless of the split. Any same-uid process can read that value from `/proc/<pid>/environ` for the child's lifetime, and it shows up in `ps e` too, so a credential stashed via `Context::addHidden()` leaks well beyond the job that set it. Applies from the 13.x context-propagation fix onward; keep credentials out of Context for concurrency work and resolve them inside the closure from config or a secret manager, or use the synchronous driver where the threat model requires it.

## Validation pitfalls

### Blank-ish strings skip every non-implicit rule

A string that trims to empty skips every non-implicit validation rule. `Validator::presentOrRuleIsImplicit` short-circuits on `is_string($value) && trim($value) === ''`, so `" "`, `"\t"`, `"\n"`, `""` bypass `array`, `boolean`, `string`, `max`, `enum` and every custom `ValidationRule` -- only the implicit set (`required*`, `present*`, `missing*`, `filled`, `accepted*`, `declined*`) still fires. This is a property of the VALUE, not of `nullable`. So an `'items.*' => 'array'` guard stops `{"section": "Bob"}` with a 422 and does not stop `{"section": " "}`, which slips past `empty()` too and reaches a handler type-hinted `array` as a `TypeError`. Fix: normalise blank-ish strings to `null` in `prepareForValidation()`, or `is_array()` at the consumer -- adding another rule does nothing, it is skipped for the same reason. Never conclude "the array rule protects this" from a non-blank-scalar 422.

### boolean rule validates but never normalises

The `boolean` validation rule validates but never normalises. `1`, `0`, `"1"`, `"0"` all pass, and `validated()` / `input()` return them unchanged, so `$validated['flag'] === true` is false for input the rule accepted -- and a strict compare against a stored default then persists a spurious override that never clears. Test payloads written with real JSON `true`/`false` decode to PHP bools and never expose it. Fix: cast at the read (`(bool) $validated['flag']`) or use `$request->boolean('flag')`, which does cast via `FILTER_VALIDATE_BOOL`. `boolean:strict` is not a built-in rule.

### distinct scope at two wildcard levels

`distinct` scopes to the leading explicit path, so at two wildcard levels it compares the whole payload. `'questions.*.options.*.option_key' => ['distinct']` reads as "unique within each question" and is not: `getLeadingExplicitAttributePath()` returns everything before the first asterisk (`questions`), and that subtree is flattened with `Arr::dot()`, so two different questions carrying the same option key are both rejected. `ignore_case` and `strict` change the comparison mode, never the scope; there is no per-parent option. The idiom is correct at one wildcard and silently changes meaning at two. Fix: drop `distinct` and de-dupe per parent in an `after()` closure, flagging every member of a colliding group rather than only the later one, so existing `assertJsonValidationErrors` paths still resolve.

### Exists/Unique self-skip after any message

`Exists` and `Unique` self-skip once the attribute has any message; the unprotected value is the one baked into the rule's SCOPE. `hasNotFailedPreviousRuleIfPresenceRule` gates exactly those two rules on `! $this->messages->has($attribute)`, so `['uuid', Rule::exists(...)]` cannot send a malformed UUID to the database, and adding `bail` changes nothing. The real 500 comes from the other side: `Rule::exists('docs', 'id')->where('owner_id', (string) $user->owner?->id)` casts `null` to `''` and compares it against a `uuid` column (Postgres `22P02`). Passing the nullable value through unchanged routes to `whereNull()` and yields a clean 422. Triage discriminator: is the suspect value the attribute being validated, or an argument to the rule? Only the second is exposed.

### Carbon::parse() year-only string pitfall

`Carbon::parse('2020')` is today at 20:20, not year 2020 -- a bare 4-digit string parses as `HHMM` time-of-day, breaking `before_or_equal:today` / `after` / `before` on year-only input. Fix: `Carbon::createFromFormat('Y', $year)->startOfYear()` + partial-date-aware rules; when migrating a field's validator type, audit its sibling validators for the same incompatibility.

### Auth guard infinite recursion via report()

A custom auth guard whose failure path calls `report()` infinitely recurses, and it is an unauthenticated DoS. Laravel's exception-report context calls `Auth::id()`, which re-enters the same guard mid-resolution, which fails again and reports again: `user() -> catch (Throwable) -> report() -> Handler::context() -> Auth::id() -> user()`. Any middleware calling `$request->user()` on such a route turns a malformed `Authorization: Bearer <garbage>` into an OOM'd worker. It presents as an HTTP-client or JWT-library bug because the fatal crash site moves between runs -- memory is already exhausted, so whichever allocation comes next dies; faking the outbound call just relocates the OOM downstream of the real consumer. Fix in the guard: a `resolving` flag returning `null` on re-entry, plus memoising the null resolution so repeated `user()` calls do not re-run the whole fetch-and-decode. Any resolver whose failure path calls `report()`, logs with auth context, or fires an event touching `Auth::user()` is a candidate.

### Backed enum serialization by case name

A backed enum serialises as `E:<len>:"<FQCN>:<CaseName>"` -- the case NAME, never the backing value -- so reordering cases is serialization-safe and renaming or removing one is not. Unserializing a removed case emits a warning and returns `false`; it does NOT raise `Enum::from()`'s `ValueError: X is not a valid backing value`, which is the message people write from memory into comments and MR descriptions. Under Laravel's `HandleExceptions` that warning becomes an `ErrorException`, so a `catch (Throwable)` decoder absorbs it and the entry degrades to a permanent MISS -- one rebuild plus one `report()` per read for the rest of its TTL. The other two shapes are worse because nothing catches them: a newly added promoted property unserializes fine and fires an `Error` at the consumer's first read, and a renamed or moved class warns not at all and serves `__PHP_Incomplete_Class` as a clean HIT. Version the cache key whenever a stored object graph's shape changes.
