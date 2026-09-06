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

Scoped to framework-level PHP. Work on php-src internals or a native PHP extension is C, not PHP: the `ia-c-systems` skill covers it, including the Zend API conventions (`gen_stub` arginfo, the request-scoped allocator, custom object handlers, `.phpt`).

## Code Style

- `declare(strict_types=1)` in every file
- Happy path last -- guards and errors first, success at the end. Early returns, no `else`.
- Comments explain *why*, never *what*. Never comment tests. If code needs a "what" comment, rename or restructure.
- No single-letter variables -- `$exception` not `$e`, `$request` not `$r`
- `?string` not `string|null`. Always specify `void`. Import classnames, never inline FQN.
- **Widening one parameter to `?T` obliges auditing every call site that forwards the same value** -- the sibling call still declares `string`, and `null` throws a `TypeError` there even with no `declare(strict_types=1)`, because coercive mode never coerces `null` into a scalar. Strictness is decided by the file the CALL is written in, never by the callee's file. Full mechanism in [common-pitfalls.md](./references/common-pitfalls.md).
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
- **A closure inside a `config/*.php` file breaks `config:cache`.** The cache file is written with `var_export`, which cannot represent a closure, so a hook registered as `fn ($event) => ...` works locally and aborts the deploy step with `Your configuration files are not serializable`. Register callables as `[SomeClass::class, 'method']` arrays. This is the opposite of `route:cache`, which serializes closure actions rather than rejecting them (Routing, below).
- **Service classes** for business logic with readonly DI: `__construct(private readonly PaymentService $payments)`
- **`#[Scoped]` resets in exactly one place in the framework: the queue worker, between jobs** -- never at a transaction boundary, so a memo filled inside `DB::transaction()` survives the rollback for the rest of the request or job. Full mechanism in [common-pitfalls.md](./references/common-pitfalls.md).
- **Action classes** (single-purpose invokable) for operations crossing service boundaries
- **Form Requests** for all validation -- never inline in controllers, never inside services. Add `toDto()` so services receive typed, pre-validated data; internal code trusts that input was validated at the boundary.
- **An ownership check in the controller body runs AFTER validation, so a foreign-but-existing id plus an invalid payload returns 422 while a non-existent id returns 404 -- an existence oracle.** Move it into `FormRequest::authorize()` with `failedAuthorization()` throwing `NotFoundHttpException`; the natural "other tenant gets 404" test posts a valid payload and cannot see it. Full mechanism in [common-pitfalls.md](./references/common-pitfalls.md).
- Conditional validation: `Rule::requiredIf()`, `sometimes`, `exclude_if`
- **`'field' => ['array:a,b']` restricts which keys may appear; it requires none of them** -- but OpenAPI generators publish that key list as the object's `required` array, so never read a generated `required` list as the endpoint's contract. Full mechanism in [common-pitfalls.md](./references/common-pitfalls.md).
- **Events + Listeners** for side effects (notifications, logging, cache invalidation) -- not in services. Name events past-tense in business terms (`OrderPlaced`, not `OrderRecordUpdated`). Carry IDs and changed facts in the payload, **not the full Eloquent model** -- `SerializesModels` re-fetches by key when a queued listener runs, so a model passed in-memory goes stale (same desync class as the observer/stale-copy pitfall below).
- Feature folder organization over type-based past ~20 models

## Production Resilience

- **Fail-fast config validation** in a service provider's `boot()`: missing API keys, invalid DSNs, misconfigured queues crash on startup, not on the first request that hits the code path.
- **Health endpoints**: `/health` (shallow, 200 if the process responds) and `/ready` (deep -- checks DB, Redis, critical services).
- **A `set -e` container entrypoint is a fail-fast contract -- only put steps there whose failure should genuinely block traffic.** Migrations and `config:cache` qualify; docs generation and optional caches do not, because their non-zero exit aborts the boot before php-fpm and the workers start. Full mechanism in [common-pitfalls.md](./references/common-pitfalls.md).

## Routing

- Scoped route model binding to prevent cross-tenant access: `Route::scopeBindings()->group(fn() => ...)`
- `Route::model('conversation', AiConversation::class)` for custom binding resolution
- API resource routes: `Route::apiResource('posts', PostController::class)` -- index/store/show/update/destroy without create/edit
- **Laravel 12 `route:cache` serializes closure actions instead of throwing `LogicException: Uses Closure`**, so a closure capturing `$this` from a service provider drags the bound container into the cached payload. It balloons but still terminates; unbounded blowup needs a real reference cycle. Fix: an invokable controller, or `use ($var)` instead of `$this`. Full mechanism in [common-pitfalls.md](./references/common-pitfalls.md).

## Migrations

- Anonymous class migrations; `snake_case` plural table names matching model convention
- Foreign keys: `$table->foreignId('user_id')->constrained()->cascadeOnDelete()`. Always index foreign keys and frequently filtered columns.
- Down method: rollback logic or `Schema::dropIfExists()` for new tables
- Separate schema and data migrations -- backfills in their own migration file, not mixed with DDL. One deliberate exception: when a single transaction is what closes a rolling-deploy null window, splitting reopens it; the lock-duration trade-off and table-size disposition live in the `ia-postgresql` skill, Migration Safety
- Renames/removals use expand-contract: add new column → backfill → switch reads → drop old (full pattern in `ia-postgresql` skill)
- Never edit a migration that has run in a shared environment -- write a new one
- **Set `public $withinTransaction = false;` for per-row commit/lock-release (resumable backfills) or statements Postgres rejects inside a transaction (`CREATE INDEX CONCURRENTLY`, `ALTER TYPE ... ADD VALUE`).** Otherwise inner `DB::transaction()` loops become savepoints, not independent commits ([pitfalls-deep.md](./references/pitfalls-deep.md)); no-op on MySQL.
- **The `migrations` row is inserted AFTER `up()` returns and outside its transaction**, so a process killed in that window leaves a committed-but-unrecorded migration and every later container re-runs `up()` into `relation already exists` -- a crash loop that bricks all further deploys. Fix: an early-return `Schema::hasTable()` guard at the top of `up()`. Full mechanism in [common-pitfalls.md](./references/common-pitfalls.md).
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
- **`updateOrCreate($match, $values)` reassigns the primary key on the update branch when `$values` carries a fillable identity column.** On the second call Eloquent runs `fill($values)->save()` and the WHERE uses the ORIGINAL key, so the row's id churns on every redelivery -- the opposite of the idempotency intended. Fix: keep `id` out of `$values`. Full mechanism in [pitfalls-deep.md](./references/pitfalls-deep.md).
- `Prunable` / `MassPrunable` with `prunable()` query for automatic stale record cleanup
- `$guarded = []` is a mass assignment vulnerability -- always explicit `$fillable`
- **A custom `CastsAttributes` whose `get()` returns an object is cached and merged BACK through `set()` on the next `save()`,** so a tolerant `tryFrom($v) ?? default()` read idiom overwrites the original stored value on any unrelated save. Fix: `public bool $withoutObjectCaching = true;` on the cast; anything preserving the stored value must read `getRawOriginal()`. Full mechanism in [pitfalls-deep.md](./references/pitfalls-deep.md).
- **`Builder::value()` and `pluck()` return the CAST attribute; `DB::table(...)->value()` returns the raw column.** A guard like `is_string($v) ? Enum::tryFrom($v) : null` silently returns `null` forever once a `$casts` entry exists -- no error, clean PHPStan, green tests. Grep every `->value()`/`->pluck()` when a diff adds a cast. Full mechanism in [pitfalls-deep.md](./references/pitfalls-deep.md).
- **With `Relation::enforceMorphMap()`, a model missing from the map throws `ClassMorphViolationException` -- from the audit layer, which is usually config-gated off under test**, so a new unmapped model passes the whole suite and 500s on the first audited write. The read side is the mirror: every morph write stores the ALIAS, so a hardcoded `where('<rel>_type', 'App\\Models\\Foo')` matches zero rows -- use `(new Foo)->getMorphClass()`. Full mechanism in [pitfalls-deep.md](./references/pitfalls-deep.md).
- **`latest()` / `orderByDesc()` on a relation that already declares an order APPENDS to it.** `hasMany(Version::class)->orderBy('created_at')` plus `->latest('created_at')->first()` compiles to `ORDER BY created_at asc, created_at desc` and returns the oldest row; a single-row fixture masks it. Fix: `reorder('created_at', 'desc')`, or a dedicated `latestVersion(): HasOne`. Full mechanism in [pitfalls-deep.md](./references/pitfalls-deep.md).

## API Resources

- `whenLoaded()` for relationships -- prevents N+1 in responses
- `when()` / `mergeWhen()` for permission-based fields; `whenPivotLoaded()` for pivot data
- `withResponse()` for custom headers, `with()` for metadata (version, pagination)
- **`parent::toArray($request)` calls the parent RESOURCE's `toArray()`, not the framework's attribute spread.** It spreads every model attribute only when the class extends `JsonResource` directly; through an ancestor resource returning an explicit array literal the column is never serialised, `$hidden` or not. Resolve the `extends` chain before claiming either. Full mechanism in [common-pitfalls.md](./references/common-pitfalls.md).
- **A nested `JsonResource` wrapping `null` serialises to JSON `null`, and the child's `toArray()` never runs** -- `filter()` replaces the value before `resolve()` reaches the child, so `Resource::make($nullable)` and an explicit ternary are byte-identical on the wire. Probe through the parent's `resolve($request)`, never `json_encode()`. Full mechanism in [common-pitfalls.md](./references/common-pitfalls.md).

## API Design

- **Contract-first**: define the API Resource (response contract) and Form Request (input contract) before writing the controller.
- Never return raw models or `toArray()` from controllers -- Resources control exactly what's serialized. Every observable field, ordering, or timing becomes a caller dependency (Hyrum's Law).
- **Add, don't modify**: new fields/endpoints over changing or removing existing ones. Deprecate first (`@deprecated` in OpenAPI/docblock), remove in a later version.
- **Consistent envelope**: `{ "success": bool, "data": ..., "error": null, "meta": {} }`. Normalize `ValidationException`, `ModelNotFoundException`, `AuthorizationException`, and application errors to `{ "success": false, "error": { "code": "...", "message": "..." } }` in the exception handler -- callers build error handling once.
- **Isolate third-party SDKs behind an adapter class.** Catch vendor exceptions (`GuzzleHttp\Exception\ClientException`, `Stripe\Exception\*`) inside the adapter and rethrow as domain exceptions (`PaymentFailedException`) -- never let a Guzzle/Stripe exception bubble into a controller or service.
- **Never return the raw vendor object** (`Stripe\Charge`, a Guzzle `Response`) from an adapter -- map it to a DTO first. Otherwise every vendor field becomes a caller dependency (Hyrum's Law), same as returning raw models on egress.
- **Third-party responses are untrusted data**: validate shape and content through the DTO before use in logic or rendering. Inject the specific client/credentials the adapter needs, not the whole config or container.
- **`Http::timeout($n)` is per redirect hop, not per logical call** -- Guzzle re-invokes the handler per hop with the same options, so the ceiling is `(max_redirects + 1) x timeout`: 90s at `timeout(15)`. Anything sized off that aggregate inherits the error (lock expiries, queue `$timeout`, SLOs). Full mechanism in [common-pitfalls.md](./references/common-pitfalls.md).

## Queues & Jobs

- Batching: `Bus::batch([...])->then()->catch()->finally()->dispatch()`; chaining: `Bus::chain([new Step1, new Step2])->dispatch()`
- Rate limiting: `Redis::throttle('api')->allow(10)->every(60)->then(fn() => ...)`
- **`ShouldBeUnique` prevents duplicate processing -- it is a de-duplication hint, not an at-least-once guarantee.** When the lock is already held, dispatch is silently discarded: no job, no exception, no log line. Fix: check the lock before dispatching where the skip is user-visible; confirm `UniqueJobSkipped` exists in the installed version before relying on it. Full mechanism in [pitfalls-deep.md](./references/pitfalls-deep.md).
- **`WithoutOverlapping` folds the job's class name into the lock key, so two job classes sharing a key do NOT serialize against each other** unless both call `->shared()`. A synchronous in-request writer takes no queue middleware, so no lock setting can serialize against it either. Fix: assert real contention (`getLockKey()` across both instances), not the middleware's public property. Full mechanism in [pitfalls-deep.md](./references/pitfalls-deep.md).
- **`WithoutOverlapping()->dontRelease()` with no `->expireAfter()` strands the lock forever on a hard kill (SIGKILL, OOM, node loss).** Every subsequent job for that key is then silently discarded, including from a reconciliation command. Fix: set a TTL safely longer than the job's worst-case runtime and keep `dontRelease()` -- the two knobs are orthogonal. Full mechanism in [pitfalls-deep.md](./references/pitfalls-deep.md).
- **`Context` cannot bleed between queued jobs -- it is flushed and rehydrated from each job's own dispatch payload before `handle()` runs.** The genuine bleed surface is Octane/Swoole/RoadRunner on the HTTP path, where the repository is an app singleton across requests. Full mechanism in [pitfalls-deep.md](./references/pitfalls-deep.md).
- **Adding a constructor parameter to a `ShouldQueue` job breaks every payload already queued, and a promoted default does not save it** -- `unserialize()` skips the constructor and restores only declaration-level defaults, which a promoted (or `readonly`) property has none of. Fix: a plain property with a declaration-level default, assigned in the constructor body, set to what an already-enqueued payload MEANT. Full mechanism in [pitfalls-deep.md](./references/pitfalls-deep.md).
- Always handle failures -- implement `failed()` on jobs

## Testing (PHPUnit)

### Diagnosing failing tests

1. Run the single failing test in isolation (`phpunit --filter test_name`) before reading app code.
2. Passes solo but fails in the suite → suspect shared state: container singletons, statics, `Carbon::setTestNow()` residue, DB state leaking between tests. A `private static` memo is the sharp case -- process-scoped, so no rollback reaches it; reset it through reflection rather than deleting it ([testing.md](./references/testing.md)).
3. Diff expected vs actual output before hypothesizing a cause.
4. Decide explicitly: test-bug or code-bug. Name which before editing either.
5. Never weaken an assertion to make it pass.

`MissingAttributeException` after `create()` usually means strict mode (`Model::shouldBeStrict()`) plus a factory omitting a column with a DB default -- Eloquent never re-reads that default. The silent case (a freshly created instance rendering JSON `null` for a required field) is worse than the thrown one. Fix on the model (`protected $attributes = [...]`), not the factory. Full mechanism in [testing.md](./references/testing.md).

### Patterns

- **Feature tests** (`tests/Feature/`): HTTP through the full stack (`getJson()`, `postJson()`) -- default for anything touching routes, controllers, or models. **Unit tests** (`tests/Unit/`): isolated services, actions, value objects.
- `RefreshDatabase` for full migration reset per test; `DatabaseTransactions` for transaction-wrap (faster, no migration testing); `DatabaseMigrations` to run and rollback per test
- Model factories for all test data -- never raw `DB::table()` inserts
- **Factories build the model inside `Model::unguarded()`, so a fixture can set a column `$fillable` rejects** -- the test then pins a row shape the runtime cannot produce, not merely one it does not. Fix: diff the factory payload's keys against `$fillable` before reading a guard test as coverage. Full mechanism in [factories.md](./references/factories.md).
- One behavior per test. Name with `test_` prefix: `test_user_can_update_own_profile`
- Assert both response status AND side effects (DB state, jobs, notifications): `assertDatabaseHas` / `assertDatabaseMissing`
- `actingAs($user)` for auth, `Sanctum::actingAs($user, ['ability'])` for API auth
- Fake facades BEFORE the action: `Queue::fake()` → act → `Queue::assertPushed(...)`; same for `Http::fake(['host/*' => Http::response(...)])` → `Http::assertSent(...)`
- `Gate::forUser($user)->allows('update', $post)` for authorization assertions
- **`assertJsonValidationErrors(['field'])` passes on ANY error for that field**, so an earlier rule in the chain -- or a service-layer `ValidationException::withMessages()` on the same key -- satisfies a test named for the rule under test. Fix: assert the message form (`['field' => 'must not be greater than']`) and delete the rule to prove which guard answered. Full mechanism in [feature-testing.md](./references/feature-testing.md).
- **Mockery cannot mock a `readonly` class** -- it generates a non-readonly subclass, which PHP 8.2+ rejects at class-load time, so the file dies with a FATAL (not a catchable exception) before any assertion runs. Fix: construct the real object (DTOs are free) or mock an interface it implements. Full mechanism in [mocking-and-faking.md](./references/mocking-and-faking.md).
- **`Http::assertSent()` passes when ANY recorded request satisfies the callback -- not every request, and not necessarily the one under test.** An early `return true` for out-of-scope requests makes every unrelated request satisfy the whole assertion on its own. Fix: return `false` for out-of-scope requests, then assert on the single request under test. Full mechanism in [mocking-and-faking.md](./references/mocking-and-faking.md).
- **`Mail::fake()` records mailables without building them, so `assertSent`/`assertQueued` never compiles the Blade view** -- a broken template still passes CI. Fix: force a render (`(new TheMailable(...))->render()` or `assertSeeInHtml()`) in at least one test per mailable. Full mechanism in [mocking-and-faking.md](./references/mocking-and-faking.md).
- **`Mail::fake()` swaps only the transport (the notification pipeline still runs); `Notification::fake()` swaps the whole dispatcher and neither `NotificationSending` nor `NotificationSent` fires.** Switching fakes to reach `assertSentTo()` silently kills listeners on those events. Fix: audit and cover those listeners separately. Full mechanism in [mocking-and-faking.md](./references/mocking-and-faking.md).
- **`throttle` middleware reads `config('cache.limiter')`, not `cache.default`, so `Cache::flush()` does not reset rate-limit counters** and tests can flake in the suite while passing alone. Fix: clear the limiter's own store in `setUp()` (`Cache::store(config('cache.limiter'))->clear()`). Full mechanism in [mocking-and-faking.md](./references/mocking-and-faking.md).
- **`force="true"` on a `phpunit.xml` `<env>` entry pins `getenv()`/`$_ENV`, not Laravel's `env()`** -- both surfaces need pinning because `config()` reads `env()` while a raw SDK falls through to its own `getenv()` chain. Fix: set both `<env force="true">` and `<server>` entries. Full mechanism in [testing.md](./references/testing.md).
- **`afterCommit` callbacks DO fire under `RefreshDatabase`** -- the belief they're deferred forever is false, but post-commit DURABILITY still isn't observable since the commit under test is a savepoint. Fix: test deferral behavior directly; verify durability claims separately. Full mechanism in [testing.md](./references/testing.md).
- **Every parallel worker running `RefreshDatabase` needs its own database** -- `artisan test --parallel` provisions one per worker, a manual `phpunit` fan-out does not, and concurrent `migrate:fresh` races leave the shared DB half-migrated. Fix: confirm no other `phpunit` process is running before launching a suite; set `DB_DATABASE` per process for intentional overlap. Full mechanism (including Postgres `max_locks_per_transaction`) in [testing.md](./references/testing.md).
- **`withToken('fake')` sets a header; it does not stub a custom guard**, so every other path still resolves through the real guard. Fix: use `actingAs($user, '<guard>')` when the intent is "this request is authenticated". Full mechanism in [testing.md](./references/testing.md).
- Coverage target: 80%+ with `pcov` or `XDEBUG_MODE=coverage` in CI

Generic test discipline (anti-patterns, mock rules, rationalization resistance): `ia-writing-tests` skill. Laravel testing deep dives: see References below.

## Common Pitfalls

Real production footguns, invisible to PHPStan and feature tests alone. Mechanism and fix for each: [common-pitfalls.md](./references/common-pitfalls.md), except where the bullet links elsewhere.

- **Query-builder `update()`** -- `Model::query()->where(...)->update([...])` and `Relation::update()` fire no model events, so observers and audit traits are bypassed.
- **A database-level FK cascade** -- fires no Eloquent events, and is a pure no-op when the parent uses `SoftDeletes`, because the trait rewrites `delete()` as an `UPDATE`.
- **Observer `deleting()` cleanup at parent scope** -- wipes every sibling's storage on a single-row delete.
- **`BelongsToMany` pivot writes** -- `attach`/`detach`/`sync`/`updateExistingPivot` fire no pivot model events without `using()`, and `sync()` reads the RAW pivot table, so a relationship-level `where` never filters it.
- **`chunkById + json_decode + mutate + json_encode + update`** -- loses any concurrent write to a jsonb column between the SELECT and the UPDATE ([pitfalls-deep.md](./references/pitfalls-deep.md)).
- **`date:<fmt>` cast format** -- reaches `$model->toArray()` only, never `JsonResource::resolve()`.
- **A string that trims to empty** -- skips every non-implicit validation rule, `nullable` or not ([pitfalls-deep.md](./references/pitfalls-deep.md)).
- **An empty array versus an absent key** -- indistinguishable through `empty()`, `?? null` and `isset()`, so a Clear-all save is a silent no-op; form encoding drops it on the wire too.
- **Nested-array validation** -- `'items.*.name'` rules do not stop `items.*` from being a scalar; always pair with `'items.*' => 'array'`.
- **`validated()`** -- rebuilds a nested key from its ruled sub-keys only and drops the rest ([pitfalls-deep.md](./references/pitfalls-deep.md)).
- **The `boolean` rule** -- validates but never normalises, so `=== true` is false for input it accepted ([pitfalls-deep.md](./references/pitfalls-deep.md)).
- **`distinct` at two wildcard levels** -- compares the whole payload, not per-parent ([pitfalls-deep.md](./references/pitfalls-deep.md)).
- **`Exists` / `Unique` self-skip after any message** -- so `bail` does not protect the query, and the exposed value is the rule's SCOPE argument ([pitfalls-deep.md](./references/pitfalls-deep.md)).
- **`DB::afterCommit`** -- prevents run-on-rollback; it does NOT retry a post-commit failure ([pitfalls-deep.md](./references/pitfalls-deep.md)).
- **An observer writing a model the caller also holds** -- leaves a stale in-memory copy that the caller's later `save()` re-clobbers ([pitfalls-deep.md](./references/pitfalls-deep.md)).
- **`Collection::unique()`** -- compares loosely, so `"00123"` and `"123"` collapse and a dedup or merge guard silently drops data; use `uniqueStrict()`.
- **`QueryException::getMessage()`** -- interpolates raw bindings plus host and database into the message.
- **`Carbon::parse('2020')`** -- is today at 20:20, not the year 2020 ([pitfalls-deep.md](./references/pitfalls-deep.md)).
- **A custom auth guard whose failure path calls `report()`** -- infinitely recurses; an unauthenticated DoS ([pitfalls-deep.md](./references/pitfalls-deep.md)).
- **A backed enum serialises as the case NAME** -- so renaming or removing a case breaks unserialization silently ([pitfalls-deep.md](./references/pitfalls-deep.md)).
- **A `composer.lock` conflict confined to `content-hash`** -- is not a lock conflict; recompute it, never hand-pick a side ([pitfalls-deep.md](./references/pitfalls-deep.md)).

## Discipline

- Simplicity first -- every change as simple as possible, minimal code impact
- Only touch what's necessary -- no unrelated changes
- No hacky workarounds -- if a fix feels wrong, step back and implement the clean solution
- New abstraction requires 3+ usage sites; otherwise inline it
- No empty catch blocks -- log or rethrow, never swallow
- Verify before declaring done: `./vendor/bin/phpstan analyse --level=8 && ./vendor/bin/phpunit` with zero warnings
- Checkpoint per stage, not only at the end: `migrate:status` after a migration, `route:list --path=<prefix>` after routing changes, `queue:work --once` after adding a job, `pint --test` before the PR -- each catches its failure class while the change is small

## Production Performance

OPcache + JIT + preloading configuration and Laravel deploy caches (`config:cache`, `route:cache`, etc.): [production-performance.md](./references/production-performance.md)

## References

- [laravel-ecosystem.md](./references/laravel-ecosystem.md) -- Notifications, Task Scheduling, Custom Casts
- [testing.md](./references/testing.md) -- PHPUnit essentials, data providers, running tests
- [feature-testing.md](./references/feature-testing.md) -- Auth, validation, API, console, DB assertions
- [mocking-and-faking.md](./references/mocking-and-faking.md) -- Facade fakes, action mocking, Mockery
- [factories.md](./references/factories.md) -- States, relationships, sequences, afterCreating hooks
- [production-performance.md](./references/production-performance.md) -- OPcache, JIT, preloading, deploy caches
- [common-pitfalls.md](./references/common-pitfalls.md) -- event-layer bypasses, FK cascades, pivot writes, resource and request-shape traps
- [pitfalls-deep.md](./references/pitfalls-deep.md) -- afterCommit alternatives, observer desync, jsonb race, savepoints, validation-rule internals
