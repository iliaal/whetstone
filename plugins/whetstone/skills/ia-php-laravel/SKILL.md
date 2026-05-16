---
name: ia-php-laravel
class: language
description: >-
  Modern PHP 8.4 and Laravel patterns: architecture, Eloquent, queues, testing.
  Use when working with Laravel, Eloquent, Blade, artisan, PHPUnit, PHPStan,
  or building/testing PHP applications with frameworks. Not for PHP internals (php-src)
  or general PHP language discussion.
paths: "**/*.php"
---

# PHP & Laravel Development

## Code Style

- `declare(strict_types=1)` in every file
- Happy path last -- handle errors/guards first, success at the end. Use early returns; avoid `else`.
- Comments only explain *why*, never *what*. Never comment tests. If code needs a "what" comment, rename or restructure instead.
- No single-letter variables -- `$exception` not `$e`, `$request` not `$r`
- `?string` not `string|null`. Always specify `void`. Import classnames everywhere, never inline FQN.
- Validation uses array notation `['required', 'email']` for easier custom rule classes
- Static analysis: run PHPStan at level 8+ (`phpstan analyse --level=8`). Aim for level 9 on new projects. Use `@phpstan-type` and `@phpstan-param` for generic collection types.

## Modern PHP (8.4)

Use these when applicable -- do not add explanatory comments in generated code (Claude and developers know them):
- Readonly classes and properties for immutable data
- Enums with methods and interfaces for domain constants
- Match expressions over switch
- Constructor promotion with readonly
- First-class callable syntax `$fn = $obj->method(...)`
- Fibers for cooperative async when Swoole/ReactPHP not available
- DNF types `(Stringable&Countable)|null` for complex constraints
- Property hooks: `public string $name { get => strtoupper($this->name); set => trim($value); }`
- Asymmetric visibility: `public private(set) string $name` -- public read, private write
- `new` without parentheses in chains: `new MyService()->handle()`
- `array_find()`, `array_any()`, `array_all()` -- native array search/check without closures wrapping Collection

## Laravel Architecture

- **Thin controllers** -- controllers only: validate, call service/action, return response. Domain behavior (scopes, accessors, relationships) lives in models; cross-cutting orchestration lives in service classes.
- **Service classes** for business logic with readonly DI: `__construct(private readonly PaymentService $payments)`
- **Action classes** (single-purpose invokable) for operations that cross service boundaries
- **Form Requests** for all validation -- never validate inline in controllers. Add `toDto()` method to convert validated data to typed service parameters.
- Conditional validation: `Rule::requiredIf()`, `sometimes`, `exclude_if` for complex form logic
- **Events + Listeners** for side effects (notifications, logging, cache invalidation). Do not put side effects in services.
- Feature folder organization over type-based when project exceeds ~20 models

## Production Resilience

- **Fail-fast config validation**: validate critical config values in a service provider's `boot()` method. Missing API keys, invalid DSNs, or misconfigured queues should crash the app on startup, not on the first request that hits the code path.
- **Health endpoints**: expose `/health` (shallow, returns 200 if the process responds) and `/ready` (deep, checks database, Redis, and critical service connectivity). Use Laravel's built-in health checks (`Illuminate\Health`) or a simple route that queries each dependency.

## Routing

- Scoped route model binding to prevent cross-tenant access: `Route::scopeBindings()->group(fn() => ...)`
- `Route::model('conversation', AiConversation::class)` for custom binding resolution
- API resource routes: `Route::apiResource('posts', PostController::class)` -- generates index/store/show/update/destroy without create/edit
- Standardized JSON response envelope: `{ "success": bool, "data": ..., "error": null, "meta": {} }`

## Migrations

- Anonymous class migrations -- no class name collisions
- `snake_case` plural table names matching model convention
- Foreign keys: `$table->foreignId('user_id')->constrained()->cascadeOnDelete()`
- Always add index on foreign keys and frequently filtered columns
- Down method: include rollback logic or `Schema::dropIfExists()` for new tables
- Separate schema and data migrations -- data backfills in their own migration file, not mixed with DDL
- Renames/removals use expand-contract: add new column → backfill → switch reads → drop old (see `ia-postgresql` skill for the full pattern)
- Never edit a migration that has run in a shared environment -- write a new one

## Eloquent

- `Model::preventLazyLoading(!app()->isProduction())` -- catch N+1 during development
- Select only needed columns: `Post::with(['user:id,name'])->select(['id', 'title', 'user_id'])`
- Bulk operations at database level: `Post::where('status', 'draft')->update([...])` -- do not load into memory to update
- `increment()`/`decrement()` for counters in a single query
- Composite indexes for common query combinations
- Chunking for large datasets (`chunk(1000)`), lazy collections for memory-constrained processing
- Query scopes (`scopeActive`, `scopeRecent`) for reusable constraints
- `withCount('comments')` / `withExists('approvals')` for aggregate subqueries -- never load relations just to count
- `->when($filter, fn($q) => $q->where(...))` for conditional query building
- `DB::transaction(fn() => ...)` -- automatic rollback on exception
- `Model::upsert($rows, ['unique_key'], ['update_cols'])` for bulk insert-or-update
- `Prunable` / `MassPrunable` trait with `prunable()` query for automatic stale record cleanup
- `$guarded = []` is a mass assignment vulnerability -- always use explicit `$fillable`

## API Resources

- `whenLoaded()` for relationships -- prevents N+1 in responses
- `when()` / `mergeWhen()` for permission-based field inclusion
- `whenPivotLoaded()` for pivot data
- `withResponse()` for custom headers, `with()` for metadata (version, pagination)

## API Design

- **Contract-first**: define the API Resource and Form Request before writing the controller. The resource is the response contract, the Form Request is the input contract -- implementation follows.
- **Hyrum's Law awareness**: every observable response field, ordering, or timing becomes a dependency for callers. Use API Resources to control exactly what's serialized -- never return raw models or `toArray()` from controllers.
- **Addition over modification**: add new fields/endpoints rather than changing or removing existing ones. Removing a field from an API Resource breaks callers silently. Deprecate first (`@deprecated` in OpenAPI/docblock), remove in a later version.
- **Consistent error envelope**: all exceptions should produce the same `{ "success": false, "error": { "code": "...", "message": "..." } }` structure. Use `Handler::render()` or a custom exception handler to normalize `ValidationException`, `ModelNotFoundException`, `AuthorizationException`, and application errors into one format. Callers build error handling once.
- **Boundary validation via Form Requests**: validate at the HTTP boundary, not inside services. Form Requests with `toDto()` ensure services receive typed, pre-validated data. Internal code trusts that input was validated at entry -- no redundant checks scattered through repositories or models.
- **Third-party responses are untrusted data**: validate shape and content of external API responses before using them in logic, rendering, or decision-making. A compromised or misbehaving service can return unexpected types, malicious content, or missing fields. Wrap in a DTO or validate through a dedicated response class before use.

## Queues & Jobs

- Job batching with `Bus::batch([...])->then()->catch()->finally()->dispatch()`
- Job chaining for sequential ops: `Bus::chain([new Step1, new Step2])->dispatch()`
- Rate limiting: `Redis::throttle('api')->allow(10)->every(60)->then(fn() => ...)`
- `ShouldBeUnique` interface to prevent duplicate processing
- Always handle failures -- implement `failed()` method on jobs

## Testing (PHPUnit)

- **Feature tests** (`tests/Feature/`): HTTP through the full stack. Use `$this->getJson()`, `$this->postJson()`, etc.
- **Unit tests** (`tests/Unit/`): Isolated logic -- services, actions, value objects. No HTTP, minimal database.
- Default to feature tests for anything touching routes, controllers, or models
- `use RefreshDatabase` for full migration reset per test. `use DatabaseTransactions` for wrapping in transaction (faster, but no migration testing). `use DatabaseMigrations` to run and rollback migrations per test.
- Model factories for all test data -- never raw `DB::table()` inserts
- One behavior per test. Name with `test_` prefix: `test_user_can_update_own_profile`
- Assert both response status AND side effects (DB state, dispatched jobs, sent notifications)
- `actingAs($user)` for auth, `Sanctum::actingAs($user, ['ability'])` for API auth
- Fake facades BEFORE the action: `Queue::fake()` then act then `Queue::assertPushed(...)`
- `Http::fake()` for outbound HTTP: `Http::fake(['api.example.com/*' => Http::response([...], 200)])` then `Http::assertSent(...)`
- `Gate::forUser($user)->allows('update', $post)` for authorization assertions
- `assertDatabaseHas` / `assertDatabaseMissing` to verify persistence
- Coverage target: 80%+ with `pcov` or `XDEBUG_MODE=coverage` in CI
For generic test discipline (anti-patterns, mock rules, rationalization resistance), see the `ia-writing-tests` skill — this skill covers Laravel-specific patterns that sit on top of that foundation.
See [testing patterns and examples](./references/testing.md) for PHPUnit essentials, data providers, and running tests.
See [feature testing](./references/feature-testing.md) for auth, validation, API, console, and DB assertions.
See [mocking and faking](./references/mocking-and-faking.md) for facade fakes and action mocking.
See [factories](./references/factories.md) for states, relationships, sequences, and afterCreating hooks.

## Common Pitfalls

Concrete Laravel footguns that recur across projects. Each is a real class of bug caught in production review; all are invisible to PHPStan and feature tests alone.

**Query-builder `update()` silently skips observers and audit events.** `Model::query()->where(...)->update([...])` and `Relation::update([...])` are query-builder operations — they do NOT fire Eloquent model events. Any observer registered via `#[ObservedBy]`, OwenIt Auditable trait, or `static::saving/updating` callback is bypassed. No audit row, no cascading cleanup, no dispatched jobs. Fix: `lockForUpdate() + save()` inside a transaction gives the same idempotent-atomic semantics while still firing events. Reach for raw mass update only with a `// intentionally bypasses <Observer>` comment documenting the bypass.

**Observer `deleting()` cleanup at parent scope nukes siblings.** If a `DocumentObserver::deleting()` calls `Storage::deleteDirectory($parent->uploadPath)` and the parent has a `hasMany` of Documents, deleting one child wipes storage for all siblings while their DB rows remain pointing at non-existent keys. Detection: when any single-row `$model->delete()` has an Observer, open `app/Observers/{Model}Observer.php` and check whether `deleting()` / `deleted()` hooks operate at parent scope or single-row scope. Fix: scope cleanup to the row's own storage paths, or move cleanup out of the observer into an Action class that knows the sibling count.

**`chunkById + json_decode + mutate + json_encode + update` loses concurrent writes on jsonb columns.** The window between the SELECT populating `$row->metadata` and the per-row UPDATE is milliseconds; any user save in that window is silently overwritten by the migration's stale snapshot. Fix: use in-place `DB::raw("jsonb_set(metadata, '{path}', ...)")` for shallow edits, or `lockForUpdate()` inside the chunk for arbitrary PHP logic. Default `chunkById + decode/encode` is only safe during a maintenance window with writes blocked.

**`date:<fmt>` cast format only reaches `$model->toArray()`, NOT `JsonResource::resolve()`.** A `JsonResource` that does `return ['started_at' => $this->resource->started_at]` emits ISO 8601 from Carbon's own `JsonSerializable`, ignoring the cast format entirely. Changing `date` to `date:m/d/Y` is NOT an API contract change unless the code path uses `$model->toArray()` directly (Filament admin, DTOs pulling from `toArray()`, direct `json_encode($model)`). Verify with a live reproducer before flagging as wire-format regression.

**Nested-array validation accepts scalar elements when only `*.field` rules are set.** Rules like `'items.*.name' => 'string'` and `'items.*.date' => 'date'` do NOT enforce that each `items.*` is itself an array. Scalar elements pass validation; the handler's `$data['items'][0]['name']` then yields `null` (string indexed as array — PHP warning, blank row written) or `TypeError` (int indexed as array — 500 to the caller). Always pair per-key rules with an explicit `'items.*' => 'array'` constraint.

**`DB::afterCommit` closes the rollback half but not the post-commit-failure half.** Wrapping an external mutation (S3, search index, third-party webhook) in `DB::afterCommit($closure)` prevents the external work from running when the transaction rolls back. It does NOT retry the external op when it fails after commit — the closure runs once, exceptions bubble out of the response cycle, the operation drops, and the DB row now advertises a state the external system doesn't reflect. Closing patterns: (a) queued job with `tries` + exponential backoff + `failed(Throwable $e)` handler that reverts the DB precondition the job was supposed to make true; (b) external-op-first-then-DB when the op is idempotent on the destination key (works for `Storage::copy`, fails for `Storage::move` after first attempt); (c) reconciler scheduled command that walks rows with stuck "in-flight" flags. Pattern (a) is the general-purpose default; queue retry semantics already model the transient/permanent split.

## Discipline

- Simplicity first -- every change as simple as possible, impact minimal code
- Only touch what's necessary -- avoid introducing unrelated changes
- No hacky workarounds -- if a fix feels wrong, step back and implement the clean solution
- Before adding a new abstraction, verify it appears in 3+ places. If not, inline it.
- No empty catch blocks -- log or rethrow, never swallow exceptions
- Verify: `./vendor/bin/phpstan analyse --level=8 && ./vendor/bin/phpunit` pass with zero warnings before declaring done

## Production Performance

For OPcache + JIT + preloading configuration and Laravel-specific deploy caches (`config:cache`, `route:cache`, etc.), load [production-performance.md](./references/production-performance.md).

## References

- [laravel-ecosystem.md](./references/laravel-ecosystem.md) -- Notifications, Task Scheduling, Custom Casts
- [testing.md](./references/testing.md) -- PHPUnit essentials, data providers, running tests
- [feature-testing.md](./references/feature-testing.md) -- Auth, validation, API, console, DB assertions
- [mocking-and-faking.md](./references/mocking-and-faking.md) -- Facade fakes, action mocking, Mockery
- [factories.md](./references/factories.md) -- States, relationships, sequences, afterCreating hooks
- [production-performance.md](./references/production-performance.md) -- OPcache, JIT, preloading, Laravel deploy caches
