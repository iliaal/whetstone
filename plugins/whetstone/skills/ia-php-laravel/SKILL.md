---
name: ia-php-laravel
class: language
description: >-
  Modern PHP 8.4 and Laravel patterns: architecture, Eloquent, migrations, queues, testing.
  Use when working with Laravel, Eloquent, Blade, artisan, or building/testing a
  framework-based PHP app. Not for php-src internals, standalone PHP libraries, or
  general PHP language discussion.
paths: "**/*.php"
---

# PHP & Laravel Development

## Code Style

- `declare(strict_types=1)` in every file
- Happy path last -- guards and errors first, success at the end. Early returns, no `else`.
- Comments explain *why*, never *what*. Never comment tests. If code needs a "what" comment, rename or restructure.
- No single-letter variables -- `$exception` not `$e`, `$request` not `$r`
- `?string` not `string|null`. Always specify `void`. Import classnames, never inline FQN.
- Validation uses array notation `['required', 'email']` for easier custom rule classes
- PHPStan level 8+ (`phpstan analyse --level=8`); aim for 9 on new projects. `@phpstan-type` / `@phpstan-param` for generic collection types. The missing-iterable-value-type check lands at **level 6** (and every level above it), so any project at 8+ inherits it: use the generic form on every iterable -- `@return Collection<int, User>`, `@param array<int, MyObject>` -- and array-shape notation `array{first: SomeClass, second: SomeClass}` for fixed-key returns; a bare `Collection` or `array` will not clear it.

## Modern PHP (8.4)

Use when applicable -- no explanatory comments for these in generated code:
- Readonly classes/properties for immutable data; constructor promotion with readonly
- Enums with methods and interfaces for domain constants
- Match expressions over switch
- First-class callable syntax `$fn = $obj->method(...)`
- Fibers for cooperative async when Swoole/ReactPHP not available
- DNF types `(Stringable&Countable)|null` for complex constraints
- Property hooks: `public string $name { get => strtoupper($this->name); set => trim($value); }`
- Asymmetric visibility: `public private(set) string $name` -- public read, private write
- `new` without parentheses in chains: `new MyService()->handle()`
- `array_find()`, `array_any()`, `array_all()` -- native array search/check without closures wrapping Collection

## Laravel Architecture

- **Escalate structure only when it pays for itself.** Simple CRUD → a fat Eloquent model + Form Request is correct; do not add layers. Reach for an **Action class** when an operation crosses model boundaries or gains a 3rd caller. Extract a **non-Eloquent domain object** only when a business rule needs testing without booting the DB, or protects an invariant the model can't. Default down the ladder, not up -- an unused abstraction is a defect, not foresight.
- **Thin controllers** -- only validate, call service/action, return response. Domain behavior (scopes, accessors, relationships) lives in models; cross-cutting orchestration in service classes.
- **Never call `env()` outside `config/`.** Wherever `php artisan config:cache` has run (the deploy sequence requires it, so typically production), every `env()` call outside a config file returns `null` -- silently, with no error. Read through `config('services.github.token')` and put third-party credentials in `config/services.php` rather than inventing a new config file.
- **Service classes** for business logic with readonly DI: `__construct(private readonly PaymentService $payments)`
- **Action classes** (single-purpose invokable) for operations crossing service boundaries
- **Form Requests** for all validation -- never inline in controllers, never inside services. Add `toDto()` so services receive typed, pre-validated data; internal code trusts that input was validated at the boundary.
- Conditional validation: `Rule::requiredIf()`, `sometimes`, `exclude_if`
- **Events + Listeners** for side effects (notifications, logging, cache invalidation) -- not in services. Name events past-tense in business terms (`OrderPlaced`, not `OrderRecordUpdated`). Carry IDs and changed facts in the payload, **not the full Eloquent model** -- `SerializesModels` re-fetches by key when a queued listener runs, so a model passed in-memory goes stale (same desync class as the observer/stale-copy pitfall below).
- Feature folder organization over type-based past ~20 models

## Production Resilience

- **Fail-fast config validation** in a service provider's `boot()`: missing API keys, invalid DSNs, misconfigured queues crash on startup, not on the first request that hits the code path.
- **Health endpoints**: `/health` (shallow, 200 if the process responds) and `/ready` (deep -- checks DB, Redis, critical services).

## Routing

- Scoped route model binding to prevent cross-tenant access: `Route::scopeBindings()->group(fn() => ...)`
- `Route::model('conversation', AiConversation::class)` for custom binding resolution
- API resource routes: `Route::apiResource('posts', PostController::class)` -- index/store/show/update/destroy without create/edit

## Migrations

- Anonymous class migrations; `snake_case` plural table names matching model convention
- Foreign keys: `$table->foreignId('user_id')->constrained()->cascadeOnDelete()`. Always index foreign keys and frequently filtered columns.
- Down method: rollback logic or `Schema::dropIfExists()` for new tables
- Separate schema and data migrations -- backfills in their own migration file, not mixed with DDL
- Renames/removals use expand-contract: add new column → backfill → switch reads → drop old (full pattern in `ia-postgresql` skill)
- Never edit a migration that has run in a shared environment -- write a new one
- **Set `public $withinTransaction = false;` for per-row commit/lock-release (resumable backfills) or statements Postgres rejects inside a transaction (`CREATE INDEX CONCURRENTLY`, `ALTER TYPE ... ADD VALUE`).** Otherwise inner `DB::transaction()` loops become savepoints, not independent commits ([pitfalls-deep.md](./references/pitfalls-deep.md)); no-op on MySQL.
- `migrate:fresh` resets only the SQL connection -- external stores (DynamoDB, S3, Redis) persist across it, so external-store data migrations re-run on already-migrated data and must be idempotent on a second run.

## Eloquent

- `Model::preventLazyLoading(!app()->isProduction())` -- catch N+1 during development
- Select only needed columns: `Post::with(['user:id,name'])->select(['id', 'title', 'user_id'])`
- Bulk operations at database level: `Post::where('status', 'draft')->update([...])` -- never load into memory to update. `increment()`/`decrement()` for counters.
- Composite indexes for common query combinations
- `chunk(1000)` for large datasets, lazy collections for memory-constrained processing
- Query scopes (`scopeActive`, `scopeRecent`) for reusable constraints
- `withCount('comments')` / `withExists('approvals')` -- never load relations just to count
- `->when($filter, fn($q) => $q->where(...))` for conditional query building
- `DB::transaction(fn() => ...)` -- automatic rollback on exception
- `Model::upsert($rows, ['unique_key'], ['update_cols'])` for bulk insert-or-update
- `Prunable` / `MassPrunable` with `prunable()` query for automatic stale record cleanup
- `$guarded = []` is a mass assignment vulnerability -- always explicit `$fillable`

## API Resources

- `whenLoaded()` for relationships -- prevents N+1 in responses
- `when()` / `mergeWhen()` for permission-based fields; `whenPivotLoaded()` for pivot data
- `withResponse()` for custom headers, `with()` for metadata (version, pagination)

## API Design

- **Contract-first**: define the API Resource (response contract) and Form Request (input contract) before writing the controller.
- Never return raw models or `toArray()` from controllers -- Resources control exactly what's serialized. Every observable field, ordering, or timing becomes a caller dependency (Hyrum's Law).
- **Add, don't modify**: new fields/endpoints over changing or removing existing ones. Deprecate first (`@deprecated` in OpenAPI/docblock), remove in a later version.
- **Consistent envelope**: `{ "success": bool, "data": ..., "error": null, "meta": {} }`. Normalize `ValidationException`, `ModelNotFoundException`, `AuthorizationException`, and application errors to `{ "success": false, "error": { "code": "...", "message": "..." } }` in the exception handler -- callers build error handling once.
- **Isolate third-party SDKs behind an adapter class.** Catch vendor exceptions (`GuzzleHttp\Exception\ClientException`, `Stripe\Exception\*`) inside the adapter and rethrow as domain exceptions (`PaymentFailedException`) -- never let a Guzzle/Stripe exception bubble into a controller or service.
- **Never return the raw vendor object** (`Stripe\Charge`, a Guzzle `Response`) from an adapter -- map it to a DTO first. Otherwise every vendor field becomes a caller dependency (Hyrum's Law), same as returning raw models on egress.
- **Third-party responses are untrusted data**: validate shape and content through the DTO before use in logic or rendering. Inject the specific client/credentials the adapter needs, not the whole config or container.

## Queues & Jobs

- Batching: `Bus::batch([...])->then()->catch()->finally()->dispatch()`; chaining: `Bus::chain([new Step1, new Step2])->dispatch()`
- Rate limiting: `Redis::throttle('api')->allow(10)->every(60)->then(fn() => ...)`
- `ShouldBeUnique` interface to prevent duplicate processing
- Always handle failures -- implement `failed()` on jobs

## Testing (PHPUnit)

### Diagnosing failing tests

1. Run the single failing test in isolation (`phpunit --filter test_name`) before reading app code.
2. Passes solo but fails in the suite → suspect shared state: container singletons, statics, `Carbon::setTestNow()` residue, DB state leaking between tests (the classic paratest failure).
3. Diff expected vs actual output before hypothesizing a cause.
4. Decide explicitly: test-bug or code-bug. Name which before editing either.
5. Never weaken an assertion to make it pass.

Test throws `MissingAttributeException` → strict mode (`Model::shouldBeStrict()`) + factory omits a column with a DB default: add the column to the factory or `->refresh()` after create.

### Patterns

- **Feature tests** (`tests/Feature/`): HTTP through the full stack (`getJson()`, `postJson()`) -- default for anything touching routes, controllers, or models. **Unit tests** (`tests/Unit/`): isolated services, actions, value objects.
- `RefreshDatabase` for full migration reset per test; `DatabaseTransactions` for transaction-wrap (faster, no migration testing); `DatabaseMigrations` to run and rollback per test
- Model factories for all test data -- never raw `DB::table()` inserts
- One behavior per test. Name with `test_` prefix: `test_user_can_update_own_profile`
- Assert both response status AND side effects (DB state, jobs, notifications): `assertDatabaseHas` / `assertDatabaseMissing`
- `actingAs($user)` for auth, `Sanctum::actingAs($user, ['ability'])` for API auth
- Fake facades BEFORE the action: `Queue::fake()` → act → `Queue::assertPushed(...)`; same for `Http::fake(['host/*' => Http::response(...)])` → `Http::assertSent(...)`
- `Gate::forUser($user)->allows('update', $post)` for authorization assertions
- Coverage target: 80%+ with `pcov` or `XDEBUG_MODE=coverage` in CI

Generic test discipline (anti-patterns, mock rules, rationalization resistance): `ia-writing-tests` skill. Laravel testing deep dives: see References below.

## Common Pitfalls

Real production footguns, invisible to PHPStan and feature tests alone. Extended mechanics and alternatives in [pitfalls-deep.md](./references/pitfalls-deep.md).

**Query-builder `update()` silently skips observers and audit events.** `Model::query()->where(...)->update([...])` and `Relation::update()` fire no model events -- observers, Auditable traits, `static::saving/updating` all bypassed. Fix: `lockForUpdate() + save()` in a transaction keeps events firing; raw mass update only with a `// intentionally bypasses <Observer>` comment.

**Observer `deleting()` cleanup at parent scope nukes siblings.** `Storage::deleteDirectory($parent->uploadPath)` on a single child delete wipes storage for all siblings while their rows still point at the keys. Detection: when a single-row `delete()` has an Observer, check whether its hooks operate at parent or row scope. Fix: scope cleanup to the row's own paths, or move it to an Action that knows the sibling count.

**`chunkById + json_decode + mutate + json_encode + update` loses concurrent writes on jsonb columns.** Any user save between the SELECT and the per-row UPDATE is silently overwritten. Fix: in-place `DB::raw("jsonb_set(...)")` for shallow edits, or `lockForUpdate()` inside the chunk; the decode/encode default is only safe with writes blocked.

**`date:<fmt>` cast format only reaches `$model->toArray()`, NOT `JsonResource::resolve()`.** A resource returning the raw attribute emits Carbon's ISO 8601, ignoring the cast -- so a cast-format change is not a wire-format change unless the path uses `toArray()` directly (Filament, DTOs, `json_encode($model)`). Verify with a live reproducer before flagging.

**Nested-array validation accepts scalar elements when only `*.field` rules are set.** `'items.*.name' => 'string'` does not enforce that each `items.*` is an array -- scalars pass, then `$data['items'][0]['name']` yields `null` (blank row) or a `TypeError` (500). Always pair per-key rules with `'items.*' => 'array'`.

**`DB::afterCommit` prevents run-on-rollback but does NOT retry post-commit failures.** Default fix: dispatch a queued job with `tries` + `failed()` that reverts the DB precondition. Alternatives in [pitfalls-deep.md](./references/pitfalls-deep.md).

**Observer writes a model the caller also holds → stale in-memory copy; the caller's later `save()` silently re-clobbers.** Fix: `$model->refresh()` after the triggering event, or `Model::withoutEvents()` when the caller owns the column.

**`BelongsToMany::attach` / `detach` / `sync` / `updateExistingPivot` are query-builder writes -- no pivot model events fire.** Observers and audit traits record nothing. Fix: make the pivot a real `Pivot` model (`->using(PivotModel::class)`) and write through it with `firstOrCreate(...)->fill([...])->save()`.

**`Carbon::parse('2020')` is today at 20:20, not year 2020** -- a bare 4-digit string parses as `HHMM` time-of-day, breaking `before_or_equal:today` / `after` / `before` on year-only input. Fix: `Carbon::createFromFormat('Y', $year)->startOfYear()` + partial-date-aware rules; when migrating a field's validator type, audit its sibling validators for the same incompatibility.

## Discipline

- Simplicity first -- every change as simple as possible, minimal code impact
- Only touch what's necessary -- no unrelated changes
- No hacky workarounds -- if a fix feels wrong, step back and implement the clean solution
- New abstraction requires 3+ usage sites; otherwise inline it
- No empty catch blocks -- log or rethrow, never swallow
- Verify before declaring done: `./vendor/bin/phpstan analyse --level=8 && ./vendor/bin/phpunit` with zero warnings

## Production Performance

OPcache + JIT + preloading configuration and Laravel deploy caches (`config:cache`, `route:cache`, etc.): [production-performance.md](./references/production-performance.md)

## References

- [laravel-ecosystem.md](./references/laravel-ecosystem.md) -- Notifications, Task Scheduling, Custom Casts
- [testing.md](./references/testing.md) -- PHPUnit essentials, data providers, running tests
- [feature-testing.md](./references/feature-testing.md) -- Auth, validation, API, console, DB assertions
- [mocking-and-faking.md](./references/mocking-and-faking.md) -- Facade fakes, action mocking, Mockery
- [factories.md](./references/factories.md) -- States, relationships, sequences, afterCreating hooks
- [production-performance.md](./references/production-performance.md) -- OPcache, JIT, preloading, deploy caches
- [pitfalls-deep.md](./references/pitfalls-deep.md) -- afterCommit alternatives, observer-desync mechanics, jsonb race, savepoint mechanics
