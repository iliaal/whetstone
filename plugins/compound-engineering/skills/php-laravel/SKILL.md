---
name: php-laravel
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
- Renames/removals use expand-contract: add new column → backfill → switch reads → drop old (see `postgresql` skill for the full pattern)
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
For generic test discipline (anti-patterns, mock rules, rationalization resistance), see the `writing-tests` skill — this skill covers Laravel-specific patterns that sit on top of that foundation.
See [testing patterns and examples](./references/testing.md) for PHPUnit essentials, data providers, and running tests.
See [feature testing](./references/feature-testing.md) for auth, validation, API, console, and DB assertions.
See [mocking and faking](./references/mocking-and-faking.md) for facade fakes and action mocking.
See [factories](./references/factories.md) for states, relationships, sequences, and afterCreating hooks.

## Discipline

- Simplicity first -- every change as simple as possible, impact minimal code
- Only touch what's necessary -- avoid introducing unrelated changes
- No hacky workarounds -- if a fix feels wrong, step back and implement the clean solution
- Before adding a new abstraction, verify it appears in 3+ places. If not, inline it.
- No empty catch blocks -- log or rethrow, never swallow exceptions
- Verify: `./vendor/bin/phpstan analyse --level=8 && ./vendor/bin/phpunit` pass with zero warnings before declaring done

## Production Performance

- **OPcache**: enable in production (`opcache.enable=1`), set `opcache.memory_consumption=256`, `opcache.max_accelerated_files=20000`. Validate with `opcache_get_status()`.
- **JIT**: enable with `opcache.jit_buffer_size=100M`, `opcache.jit=1255` (tracing). Biggest gains on CPU-bound code (math, loops), minimal impact on I/O-bound Laravel requests.
- **Preloading**: `opcache.preload=preload.php` -- preload framework classes and hot app classes. Use `composer dumpautoload --classmap-authoritative` in production.
- **Laravel-specific**: `php artisan config:cache && php artisan route:cache && php artisan view:cache && php artisan event:cache` -- run on every deploy. `composer install --optimize-autoloader --no-dev` for production.

## References

- [laravel-ecosystem.md](./references/laravel-ecosystem.md) -- Notifications, Task Scheduling, Custom Casts
- [testing.md](./references/testing.md) -- PHPUnit essentials, data providers, running tests
- [feature-testing.md](./references/feature-testing.md) -- Auth, validation, API, console, DB assertions
- [mocking-and-faking.md](./references/mocking-and-faking.md) -- Facade fakes, action mocking, Mockery
- [factories.md](./references/factories.md) -- States, relationships, sequences, afterCreating hooks
