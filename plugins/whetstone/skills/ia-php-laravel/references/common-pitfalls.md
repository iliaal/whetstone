# Laravel Common Pitfalls: mechanism and fix

Mechanism and fix for the one-line entries in SKILL.md's Common Pitfalls list, plus the request-lifecycle and resource entries linked from Laravel Architecture and API Resources. Entries whose SKILL.md bullet links to `pitfalls-deep.md` are documented there instead; nothing is repeated across the two files.

## Model events and observers

### Query-builder update() bypasses the event layer

`Model::query()->where(...)->update([...])` and `Relation::update()` are query-builder writes: no model events fire, so observers, `Auditable` traits and `static::saving` / `static::updating` hooks are all bypassed. Anything those hooks enforce (an audit row, a search-index sync, a derived-column refresh) is silently void on that path. Fix: `lockForUpdate()` + `save()` inside a transaction keeps events firing; take the raw mass update only with an explicit `// intentionally bypasses <Observer>` comment naming what is skipped.

### FK cascades and the Eloquent event layer are different layers

`->cascadeOnDelete()` is a database constraint. The two failures are mirror images and both are silent.

**The cascade fires and the event layer does not.** The database removes the children itself, Eloquent never loads or deletes them, no `deleted` event fires, and no observer, `Auditable` trait, search sync or storage cleanup runs for them, while the parent's own delete IS audited, so the log looks populated and contains no record of what the cascade took with it. The tell in review: a sibling path in the same codebase deleting children row by row with a comment explaining why. That comment is the codebase saying it depends on model events, so every FK cascade in that family is a hole in whatever the events enforce.

**The cascade does not fire at all when the parent soft-deletes.** `SoftDeletes` intercepts `delete()` at the model layer and rewrites it as `UPDATE ... SET deleted_at = ...`; `ON DELETE CASCADE` only fires on real `DELETE` SQL. The parent row stays alive, the children's FK still points at a live row, and the cascade is a pure no-op for every path that calls `$parent->delete()`, usually the dominant one. It applies only to the `forceDelete()` minority, with no warning at migration time and no failure at runtime. Same trap in any ORM that overlays soft delete on an SQL referential action.

When a change adds a delete path on a parent, answer both: do the children die by cascade or row by row, and does the parent use `SoftDeletes`? `grep` the parent model for `use SoftDeletes;` and classify every `->delete()` / `->forceDelete()` call site. Delete per row inside the transaction wherever an event-layer invariant must hold. On the test side, write cascade assertions as `$parent->forceDelete()`: `forceDelete()` is defined on the base Eloquent `Model`, not only on the trait, so it is safe to write before `SoftDeletes` lands and stays green when the trait arrives from the target branch (verify at the pinned version rather than trusting that).

### Observer deleting() cleanup at parent scope nukes siblings

`Storage::deleteDirectory($parent->uploadPath)` in a child's `deleting()` observer wipes storage for every sibling while their rows still point at the deleted keys. Detection: when a single-row `delete()` has an observer, check whether each hook operates at row scope or parent scope. Fix: scope the cleanup to the row's own paths, or move it to an Action that knows the sibling count.

### BelongsToMany pivot writes fire no model events without using()

`attach` / `detach` / `sync` / `updateExistingPivot` are query-builder writes: without `using()`, no pivot model events fire and observers and audit traits record nothing. Fix: make the pivot a real `Pivot` model (`->using(PivotModel::class)`) and write through it with `firstOrCreate(...)->fill([...])->save()`.

Qualification for one path: `syncWithoutDetaching([$id => [...]])` is attach-or-UPDATE, not insert-only, and `using()` decides both idempotency and whether events fire. It is `sync($ids, false)` (the `false` disables detaching and nothing else), and `attachNew()` routes an already-attached id with a non-empty attribute array to `updateExistingPivot()`. Without `using()` that is an unconditional `UPDATE` plus pivot timestamps and no model events, so re-running with the same value still writes. With `using(CustomPivot::class)` it is dirty-checked through `fill()->isDirty()`, issues no query when unchanged, and DOES fire normal Eloquent events on the pivot subclass. "Is it idempotent?" is answered by `grep -n 'using(' <Model>.php`; "does it clobber?" is answered by the pivot column's value set (a two-case enum has nothing to lose; a `draft`/`verified`/`completed` status does).

**`sync()` reads the RAW pivot table, so a relationship-level `where` does not filter it.** `sync()` / `syncWithoutDetaching()` resolve the current attachments through `getCurrentlyAttachedPivots()` -> `newPivotQuery()`, and `newPivotQuery()` is built on `newPivotStatement()` = `$this->query->getQuery()->newQuery()->from($table)`, a fresh builder inheriting none of the relationship's constraints. It re-applies only `pivotWheres`, `pivotWhereIns` and `pivotWhereNulls` (populated by `wherePivot()` / `wherePivotIn()` / `wherePivotNull()`) plus the parent-key constraint. So a soft-delete filter written as `belongsToMany(...)->whereNull('pivot_table.deleted_at')` does NOT reach sync's current-set query: the soft-deleted row counts as attached, sync skips it, and nothing is re-inserted or revived. That makes "sync resurrects a soft-deleted pivot" a false positive for that shape, and it makes the intended hiding not work for `wherePivot`-style filtering either. Only `wherePivotNull('deleted_at')`, `wherePivot(...)`, or a `using(SoftDeletingPivot)` pivot reaches it. Decide by reading which builder the filter lands on, not by the relationship's apparent semantics. Version caveat: the closure form `wherePivot(fn ($q) => ...)` is recorded into `pivotWheres` (and so reaches `sync()`, `detach()`, and `updateExistingPivot()`) only from Laravel 13.31.0 (framework PR #61488); earlier releases applied the closure to the relationship query and silently dropped it from the pivot query, so on those versions only the scalar `wherePivot($column, $op, $value)` form is safe for this purpose.

## Serialisation and resources

### date:<fmt> cast format reaches toArray(), not JsonResource::resolve()

A `date:<fmt>` cast changes `$model->toArray()` and nothing else. A resource returning the raw attribute emits Carbon's ISO 8601 and ignores the cast, so a cast-format change is not a wire-format change unless the path uses `toArray()` directly (Filament, DTO hydration, `json_encode($model)`). Verify with a live reproducer through the real serialisation path before flagging either direction.

### A nested JsonResource wrapping null never runs the child's toArray()

`ConditionallyLoadsAttributes::filter()` replaces the whole value on `$value instanceof self && is_null($value->resource)` before `resolve()` reaches the child, so the nested resource serialises to JSON `null` and an overriding `toArray()` that would fatal on a null resource is never entered. `Resource::make($nullable)` and an explicit `$nullable ? Resource::make(...) : null` are byte-identical on the wire. The base-class `is_null($this->resource) => []` guard is not the mechanism and is overridden in every real resource.

Probe resource serialisation through the parent's `resolve($request)`. `json_encode(['k' => Child::make(null)])` skips `filter()` entirely and throws, which reads as a production 500 and is not one.

### parent::toArray() in a resource subclass is the parent RESOURCE's whitelist

`JsonResource::toArray()` returns `$this->resource->toArray()` (every non-hidden model attribute), so `$data = parent::toArray($request)` reads as "this serialises the whole model, and a newly added sensitive column leaks unless it is in `$hidden`". That holds only when the resource extends `JsonResource` or `ResourceCollection` **directly**. When it extends another resource, `parent::` is that resource's `toArray()`, which is usually an explicit field whitelist that never touches the new column, and the attribute is not serialised at all, regardless of `$hidden`.

`parent::` is a call up the class hierarchy, not a synonym for the framework default. Resolve the `extends` chain to the class that actually extends `JsonResource` and read that class's `toArray()`; if any ancestor returns an explicit array literal, the spread stops there. Confirm with a grep for the column name across the resource directory; zero hits is dispositive. The inverse mistake is just as real, so the rule is symmetric: read the resolved `toArray()`, never infer it from the base class name.

## Validation and request shape

### Nested-array validation accepts scalar elements

`'items.*.name' => 'string'` does not enforce that each `items.*` is an array. Scalars pass, and then `$data['items'][0]['name']` yields `null` (a blank row) or a `TypeError` (a 500). Always pair per-key rules with `'items.*' => 'array'`.

### array:a,b restricts which keys may appear and requires none of them

`'field' => ['array:a,b']` is a whitelist, not a requirement; pairing it with per-key `sometimes` rules is the intended shape. The trap is downstream: OpenAPI generators publish that key list as the object's `required` array, so the generated request contract marks every key of a section mandatory while every per-key rule is optional, and a `sometimes|nullable` enum key publishes as required AND non-nullable. Never read a generated `required` list as the endpoint's contract; open the FormRequest. The control that proves the list is evidence about `array:` and not about the endpoint: a sibling field with a bare `array` rule emits no `required` at all.

### Empty arrays and absent keys collapse under empty() or truthiness

`empty($data['key']) ? null : ...` as an absence test cannot distinguish `{"key": []}` from a key that was never sent; a plain truthiness check also loses that distinction. `isset()` and `?? null` distinguish an empty array from absence, but conflate an explicit `null` with absence. Use `array_key_exists()` when key presence must remain distinct even for `null`. An `empty()` guard on a Remove / Clear-all affordance can silently skip the emptied collection: 200, nothing written, and a refetch restores what the user deleted. Removing *some* items works, because a non-empty array is not `empty`, so the defect is exactly the remove-all case. Say so, or the report reads as "the whole feature is broken" and cannot be reproduced.

Two amplifiers. Form and query encoding genuinely drop empty arrays (`http_build_query(['key' => [], 'other' => 'v'])` is `other=v`), so over `x-www-form-urlencoded` or `multipart/form-data` the empty collection and the absent key are the same bytes and no server-side guard can recover the distinction; a payload that must carry "explicitly empty" needs a JSON body. And a probe that builds the request with form parameters measures the absent case under an "empty" label, returning the right answer for the wrong reason; a non-empty control passes and proves nothing, because a non-empty array survives encoding. Print the parsed input's own `array_key_exists` verdict and run three rows: empty, non-empty, genuinely absent.

Widening the gate so `[]` means "clear" is a producer-side change, not just a consumer-side one: every upstream hook that can synthesise an empty collection (`prepareForValidation()`, a normaliser that `merge()`s filtered rows back, a serializer default) now reaches a destructive branch, and it runs before the validator, so the per-item `required` rules never see those shapes. Sweep the request pipeline for `merge(`, `replace(`, `array_filter`, `?? []` before shipping the one-line fix.

### FormRequest authorize() = true plus a controller-body 404 leaks existence

`ValidatesWhenResolvedTrait::validateResolved()` runs `prepareForValidation()`, then `passesAuthorization()`, then validation, and only then does the controller body run. An ownership check written as `abort_if(...)` / `abort(404)` inside the controller therefore sits *after* validation, so a foreign-but-existing id combined with an invalid body returns 422 while a non-existent id returns 404 at route binding. An authenticated caller separates "belongs to another tenant" from "does not exist" by probing with `{}`. The same shape appears when a FormRequest with no `authorize()` runs an `after()` closure that does a global lookup: it 422s on existence before the controller's `$this->authorize(...)` can 403.

Tests mask it almost universally, because the natural "other tenant gets 404" test posts a *valid* payload and the controller check fires. Fix: move the ownership and type check into `FormRequest::authorize()` and override `failedAuthorization()` to `throw new NotFoundHttpException`. Regression test shape: foreign-but-existing id plus an empty body must return 404, not 422.

## Authentication and sessions

### AuthenticateSession baselines the password hash on first pass, not at login

`Illuminate\Session\Middleware\AuthenticateSession` (`auth.session`) establishes its baseline lazily: `if (! $request->session()->has('password_hash_'.$driver)) { $this->storePasswordHashInSession($request); }`, then compares the user's current hash against that stored value and logs the session out on mismatch. The baseline is therefore whatever the hash happened to be the **first time the middleware ran for that session**, not the hash at login. If the login route is not itself covered by the middleware and the password changes before any request on the session passes through it, the middleware stores the post-change hash as the baseline and the mismatch never occurs. "Log out other devices on password change" is silently defeated: no exception, no log line, the old session keeps working.

The typical shape: `auth.session` applied to the authenticated route group, login and password-reset routes outside it, and a device that logs in and then goes idle while the password is rotated elsewhere. Rule: any application relying on password-change session invalidation must confirm the login path itself passes through `AuthenticateSession`, not only the routes it protects; read the `route:list --path=login` middleware column rather than the group definition. A pending framework change stores the hash at `SessionGuard::login()` time, which closes the window; still verify coverage in the installed version rather than relying on which side of that change it sits, because the invariant is "baseline written at login", and a middleware-only setup only satisfies it when the login request is covered. Regression test: log in on session A, change the password on session B without touching A, then make one request on A and assert it is logged out.

## Collections

### Collection::unique() compares loosely

`Collection::unique($key = null, $strict = false)` defaults to loose comparison: with no key it is `array_unique($items, SORT_REGULAR)`, and with a key it is `in_array($id, $exists, false)`. PHP compares two numeric-looking strings as numbers, so `"00123" == "123"` and `"1e3" == "1000"` collapse to one element. Any dedup, merge or conflict-detection step that leans on `->unique()` to decide "are these the same value?" silently treats distinct identity strings as equal: a merge-or-throw design that counts distinct values then sees `count() === 1`, concludes there is no conflict, and drops the row that held the other value. Fix: `->uniqueStrict()` (byte equality) for identity columns that can hold numeric-looking values: ids, phone numbers, ZIPs, licence and visa numbers, any code with leading zeros. Same rule for `array_unique` without `SORT_STRING` and `in_array` without `$strict`.

## Logging and exceptions

### QueryException::getMessage() interpolates raw bindings

The message carries the query's raw bindings plus the host and database name, so any log sink or APM that records exception messages leaks parameter values on every failed query. Recent versions add a per-connection `mask_bindings_in_exception_messages` option (env `DB_MASK_BINDINGS`), default off; enable it in production where query exceptions reach logs, after confirming the option exists in the installed version.

## PHP type semantics

### Widening one parameter to ?T obliges auditing every call site that forwards the value

The sibling call downstream still declares `string`, and `null` throws a `TypeError` there, including in a file with no `declare(strict_types=1)`, because coercive mode coerces between scalars and never coerces `null` into one. The PHP 8.1 "passing null to parameter of type string is deprecated" behaviour is internal-functions-only; user functions have thrown on `null` since PHP 7.0. So "no strict_types, it'll coerce" is not a safety net, and the crash lands on the exact null-input case the widening was for.

The mode is decided by the file the CALL is written in, never by the file declaring the callee, so "the callee declares strict types, therefore this 500s" is a phantom; read the caller's first lines. Where the caller is coercive the boundary silently coerces instead of throwing (an object carrying `__toString()` becomes a string), and the follow-up question is whether that string is usable downstream, not whether it threw. `php -r` is coercive; adding `declare(strict_types=1);` to the same snippet reproduces a strict caller, so both modes are one command apart.

## Container lifetimes

### #[Scoped] resets in exactly one place: the queue worker, between jobs

`forgetScopedInstances()` has a single caller, so under PHP-FPM `#[Scoped]` and `#[Singleton]` are indistinguishable (a fresh container per request resets everything anyway), and Octane does not reset it on the HTTP path unless the app wires it. None of the reset points is a database transaction boundary: a scoped service that fills a memo from rows written inside `DB::transaction()` keeps that memo after the rollback, for the rest of the request or job.

Lazy invalidation (`unset` the key, re-query on the next read) is rollback-safe by construction. Converting it to a write-through refill as an optimisation silently trades that away, and no test that never rolls back mid-request will show it.

## Deploy and boot

### A set -e container entrypoint is a fail-fast contract

Only put steps in it whose failure should genuinely block traffic. Migrations and `config:cache` qualify. Docs generation, optional caches, and any strict artisan command that exits non-zero on one bad annotation do not: the non-zero exit aborts the entrypoint before php-fpm and the workers start, so the container never boots and every deploy of that image fails. Amplifier to check for: a step that only runs outside local (`if ($this->app->isLocal()) return;`) is green on the author's machine and bricks staging and production only. Move non-critical steps after the workers start, or wrap them so a failure degrades that one feature (a 404 docs page) rather than the service.

### route:cache serializes closure actions rather than rejecting them

Laravel 12 `route:cache` no longer throws `LogicException: Uses Closure`. `Route::prepareForSerialization()` hands the action to `SerializableClosure`, which serializes whatever `$this` closed over, and a closure that captures `$this` from a service provider drags the bound application container in with it, so the cached payload balloons. Verified on Laravel 12.68 it still terminates: it serializes, it does not diverge. Unbounded blowup (`Maximum call stack size / Infinite recursion?`) requires an actual reference cycle, for example the provider storing the closure back onto its own property, which the container then re-serializes on the next pass.

Plain closure routes cache fine; group and middleware closures are fine; only serialized ACTION closures matter. Fix: move the handler to an invokable controller, or capture a local `use ($var)` instead of reaching through `$this`. Verify with `php artisan route:cache; echo $?` with the route present and removed. This is the opposite of `config:cache`, which cannot represent a closure at all and aborts the deploy step.

## Migrations

### The migrations row is written after up() returns and outside its transaction

`Migrator::runUp()` calls `runMigration()` and then, as a separate statement, `repository->log()`. A process killed in that window leaves a committed-but-unrecorded migration. On a deploy model that runs `migrate --force` at container preboot and can kill the task mid-boot, the migration stays "pending", every subsequent container re-runs `up()`, hits `relation already exists` / `type already exists`, and crash-loops, bricking every further deploy, not just this one.

Fix with an early-return idempotency guard at the top of `up()`: `if (Schema::hasTable('the_main_table')) { return; }`. That single-object guard is a valid proxy for "everything exists" ONLY if the whole body is one transaction; any statement Postgres cannot run inside a transaction is skipped on re-run and ships a partial schema (`ia-postgresql` skill, Migration Safety core rules).

## Outbound HTTP

### Http::timeout() is per redirect hop, not per logical call

It becomes `CURLOPT_TIMEOUT_MS` on one curl handle, and Guzzle follows redirects itself: `RedirectMiddleware` re-invokes the handler per hop with the same options, so each hop gets a fresh full budget. With the default `max` of 5 the ceiling is `(max_redirects + 1) x timeout`: 90s at `timeout(15)`, not 15s.

A hanging endpoint IS bounded correctly, because curl aborts the hop and the exception ends the call, so `rows x timeout` is the right figure for "every request hangs" and the wrong one for a worst case, since six hops each answering just under the timeout reaches `6N`. Anything sized off that aggregate inherits the error: a `withoutOverlapping()` expiry, a queue `$timeout`, a task timeout, an SLO. `Http::fake()` does not model redirect latency, so this is not reproducible in a test.
