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
- **Widening one parameter to `?T` obliges auditing every call site that forwards the same value.** The sibling call downstream still declares `string`, and `null` throws a `TypeError` there -- including in a file with no `declare(strict_types=1)`, because coercive mode coerces between scalars and never coerces `null` into one. The PHP 8.1 "passing null to parameter of type string is deprecated" behaviour is internal-functions-only; user functions have thrown on `null` since PHP 7.0. So "no strict_types, it'll coerce" is not a safety net, and the crash lands on the exact null-input case the widening was for.
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
- **`#[Scoped]` resets in exactly one place in the framework: the queue worker, between jobs.** `forgetScopedInstances()` has a single caller, so under PHP-FPM `#[Scoped]` and `#[Singleton]` are indistinguishable (a fresh container per request resets everything anyway) and Octane does not reset it on the HTTP path unless the app wires it. None of the reset points is a database transaction boundary: a scoped service that fills a memo from rows written inside `DB::transaction()` keeps that memo after the rollback, for the rest of the request or job. Lazy invalidation (`unset` the key, re-query on the next read) is rollback-safe by construction; converting it to a write-through refill as an optimisation silently trades that away, and no test that never rolls back mid-request will show it.
- **Action classes** (single-purpose invokable) for operations crossing service boundaries
- **Form Requests** for all validation -- never inline in controllers, never inside services. Add `toDto()` so services receive typed, pre-validated data; internal code trusts that input was validated at the boundary.
- Conditional validation: `Rule::requiredIf()`, `sometimes`, `exclude_if`
- **`'field' => ['array:a,b']` restricts which keys may appear; it requires none of them.** Pairing it with per-key `sometimes` rules is the intended shape, but OpenAPI generators publish that key list as the object's `required` array -- so the generated request contract can mark every key of a section mandatory while every per-key rule is optional, and a `sometimes|nullable` enum key publishes as required AND non-nullable. Never read a generated `required` list as the endpoint's contract; open the FormRequest. A sibling field with a bare `array` rule emits no `required` at all, which is the control that proves the list is evidence about `array:` and not about the endpoint.
- **Events + Listeners** for side effects (notifications, logging, cache invalidation) -- not in services. Name events past-tense in business terms (`OrderPlaced`, not `OrderRecordUpdated`). Carry IDs and changed facts in the payload, **not the full Eloquent model** -- `SerializesModels` re-fetches by key when a queued listener runs, so a model passed in-memory goes stale (same desync class as the observer/stale-copy pitfall below).
- Feature folder organization over type-based past ~20 models

## Production Resilience

- **Fail-fast config validation** in a service provider's `boot()`: missing API keys, invalid DSNs, misconfigured queues crash on startup, not on the first request that hits the code path.
- **Health endpoints**: `/health` (shallow, 200 if the process responds) and `/ready` (deep -- checks DB, Redis, critical services).
- **A `set -e` container entrypoint is a fail-fast contract -- only put steps there whose failure should genuinely block traffic.** Migrations and `config:cache` qualify. Docs generation, optional caches, and any strict artisan command that exits non-zero on one bad annotation do not: the non-zero exit aborts the entrypoint before php-fpm and the workers start, so the container never boots and every deploy of that image fails. Amplifier to check for: a step that only runs outside local (`if ($this->app->isLocal()) return;`) is green on the author's machine and bricks staging and production only. Move non-critical steps after the workers start, or wrap them so a failure degrades that one feature (a 404 docs page) rather than the service.

## Routing

- Scoped route model binding to prevent cross-tenant access: `Route::scopeBindings()->group(fn() => ...)`
- `Route::model('conversation', AiConversation::class)` for custom binding resolution
- API resource routes: `Route::apiResource('posts', PostController::class)` -- index/store/show/update/destroy without create/edit
- **Laravel 12 `route:cache` serializes closure actions instead of throwing `LogicException: Uses Closure`, and a closure that captures `$this` from a service provider serializes the bound container along with it.** `Route::prepareForSerialization()` now hands the action to `SerializableClosure`, which serializes whatever `$this` closed over -- a provider holds the application container, so the cached payload balloons but, verified on Laravel 12.68, still terminates: it serializes, it does not diverge. Unbounded blowup (`Maximum call stack size / Infinite recursion?`) requires an actual reference cycle, e.g. the provider storing the closure back onto its own property, which the container then re-serializes on the next pass. Plain closure routes cache fine; group and middleware closures are fine; only serialized ACTION closures matter. Fix: move the handler to an invokable controller, or capture a local `use ($var)` instead of reaching through `$this`. Verify with `php artisan route:cache; echo $?` with the route present and removed.

## Migrations

- Anonymous class migrations; `snake_case` plural table names matching model convention
- Foreign keys: `$table->foreignId('user_id')->constrained()->cascadeOnDelete()`. Always index foreign keys and frequently filtered columns.
- Down method: rollback logic or `Schema::dropIfExists()` for new tables
- Separate schema and data migrations -- backfills in their own migration file, not mixed with DDL. One deliberate exception: when a single transaction is what closes a rolling-deploy null window, splitting reopens it; the lock-duration trade-off and table-size disposition live in the `ia-postgresql` skill, Migration Safety
- Renames/removals use expand-contract: add new column → backfill → switch reads → drop old (full pattern in `ia-postgresql` skill)
- Never edit a migration that has run in a shared environment -- write a new one
- **Set `public $withinTransaction = false;` for per-row commit/lock-release (resumable backfills) or statements Postgres rejects inside a transaction (`CREATE INDEX CONCURRENTLY`, `ALTER TYPE ... ADD VALUE`).** Otherwise inner `DB::transaction()` loops become savepoints, not independent commits ([pitfalls-deep.md](./references/pitfalls-deep.md)); no-op on MySQL.
- **The `migrations` row is inserted AFTER `up()` returns and outside its transaction, so a process killed in that window leaves a committed-but-unrecorded migration.** `Migrator::runUp()` calls `runMigration()` and then, as a separate statement, `repository->log()`. On a deploy model that runs `migrate --force` at container preboot and can kill the task mid-boot, the migration stays "pending", every subsequent container re-runs `up()`, hits `relation already exists` / `type already exists`, and crash-loops -- bricking all further deploys. Fix with an early-return idempotency guard at the top of `up()`: `if (Schema::hasTable('the_main_table')) { return; }`. That single-object guard is a valid proxy for "everything exists" ONLY if the whole body is one transaction; any statement Postgres cannot run inside one is skipped on re-run and ships a partial schema (`ia-postgresql` skill, Migration Safety core rules).
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
- **A custom `CastsAttributes` whose `get()` returns an object is cached and merged BACK through `set()` on the next `save()`,** so a tolerant `tryFrom($v) ?? default()` read idiom overwrites the original stored value on any unrelated save. Fix: `public bool $withoutObjectCaching = true;` on the cast; anything preserving the stored value must read `getRawOriginal()`. Full mechanism in [pitfalls-deep.md](./references/pitfalls-deep.md).
- **`Builder::value()` and `pluck()` return the CAST attribute; `DB::table(...)->value()` returns the raw column.** A guard like `is_string($v) ? Enum::tryFrom($v) : null` silently returns `null` forever once a `$casts` entry exists for that column -- no error, clean PHPStan, green tests. Fix: accept both shapes (`$v instanceof Enum ? $v : (is_string($v) ? Enum::tryFrom($v) : null)`); grep every `->value()`/`->pluck()` call when a diff adds a cast. Full mechanism in [pitfalls-deep.md](./references/pitfalls-deep.md).
- **With `Relation::enforceMorphMap()`, a model missing from the map throws `ClassMorphViolationException` -- and almost nothing calls the triggering method except the audit layer, which is usually config-gated off under test.** So a new unmapped model passes the whole suite and 500s on the first write once auditing is on, rolling back the whole request. Fix: add the map entry in the same commit as the model; a green suite is not evidence when the audit flag is off under test. Full mechanism in [pitfalls-deep.md](./references/pitfalls-deep.md).

## API Resources

- `whenLoaded()` for relationships -- prevents N+1 in responses
- `when()` / `mergeWhen()` for permission-based fields; `whenPivotLoaded()` for pivot data
- `withResponse()` for custom headers, `with()` for metadata (version, pagination)
- **A nested `JsonResource` wrapping `null` serialises to JSON `null`, and the child's `toArray()` never runs.** `ConditionallyLoadsAttributes::filter()` replaces the whole value on `$value instanceof self && is_null($value->resource)` before `resolve()` reaches the child -- so an overriding `toArray()` that would fatal on a null resource is never entered, and `Resource::make($nullable)` and an explicit `$nullable ? Resource::make(...) : null` are byte-identical on the wire. The base-class `is_null($this->resource) => []` guard is not the mechanism and is overridden in every real resource. Probe resource serialisation through the parent's `resolve($request)`; `json_encode(['k' => Child::make(null)])` skips `filter()` entirely and throws, which reads as a production 500 and is not one.

## API Design

- **Contract-first**: define the API Resource (response contract) and Form Request (input contract) before writing the controller.
- Never return raw models or `toArray()` from controllers -- Resources control exactly what's serialized. Every observable field, ordering, or timing becomes a caller dependency (Hyrum's Law).
- **Add, don't modify**: new fields/endpoints over changing or removing existing ones. Deprecate first (`@deprecated` in OpenAPI/docblock), remove in a later version.
- **Consistent envelope**: `{ "success": bool, "data": ..., "error": null, "meta": {} }`. Normalize `ValidationException`, `ModelNotFoundException`, `AuthorizationException`, and application errors to `{ "success": false, "error": { "code": "...", "message": "..." } }` in the exception handler -- callers build error handling once.
- **Isolate third-party SDKs behind an adapter class.** Catch vendor exceptions (`GuzzleHttp\Exception\ClientException`, `Stripe\Exception\*`) inside the adapter and rethrow as domain exceptions (`PaymentFailedException`) -- never let a Guzzle/Stripe exception bubble into a controller or service.
- **Never return the raw vendor object** (`Stripe\Charge`, a Guzzle `Response`) from an adapter -- map it to a DTO first. Otherwise every vendor field becomes a caller dependency (Hyrum's Law), same as returning raw models on egress.
- **Third-party responses are untrusted data**: validate shape and content through the DTO before use in logic or rendering. Inject the specific client/credentials the adapter needs, not the whole config or container.
- **`Http::timeout($n)` is per redirect hop, not per logical call.** It becomes `CURLOPT_TIMEOUT_MS` on one curl handle, and Guzzle follows redirects itself -- `RedirectMiddleware` re-invokes the handler per hop with the same options, so each hop gets a fresh full budget. With the default `max` of 5 the ceiling is `(max_redirects + 1) x timeout`: 90s at `timeout(15)`, not 15s. A hanging endpoint IS bounded correctly (curl aborts the hop, the exception ends the call), so `rows x timeout` is right for "every request hangs" and wrong as a worst case -- six hops each answering just under the timeout reaches `6N`. Anything sized off that aggregate inherits the error: a `withoutOverlapping()` expiry, a queue `$timeout`, a task timeout, an SLO. `Http::fake()` does not model redirect latency, so it is not reproducible in a test.

## Queues & Jobs

- Batching: `Bus::batch([...])->then()->catch()->finally()->dispatch()`; chaining: `Bus::chain([new Step1, new Step2])->dispatch()`
- Rate limiting: `Redis::throttle('api')->allow(10)->every(60)->then(fn() => ...)`
- **`ShouldBeUnique` prevents duplicate processing -- it is a de-duplication hint, not an at-least-once guarantee.** When the lock is already held, dispatch is silently discarded: no job, no exception, no log line. Fix: check the lock before dispatching where the skip is user-visible; confirm `UniqueJobSkipped` exists in the installed version before relying on it. Full mechanism in [pitfalls-deep.md](./references/pitfalls-deep.md).
- **`WithoutOverlapping` folds the job's class name into the lock key, so two job classes sharing a key do NOT serialize against each other** unless both call `->shared()`. A synchronous in-request writer takes no queue middleware, so no lock setting can serialize against it either. Fix: assert real contention (`getLockKey()` across both instances), not the middleware's public property. Full mechanism in [pitfalls-deep.md](./references/pitfalls-deep.md).
- **`WithoutOverlapping()->dontRelease()` with no `->expireAfter()` strands the lock forever on a hard kill (SIGKILL, OOM, node loss).** Every subsequent job for that key is then silently discarded, including from a reconciliation command. Fix: set a TTL safely longer than the job's worst-case runtime and keep `dontRelease()` -- the two knobs are orthogonal. Full mechanism in [pitfalls-deep.md](./references/pitfalls-deep.md).
- **`Context` cannot bleed between queued jobs -- it is flushed and rehydrated from each job's own dispatch payload before `handle()` runs.** The genuine bleed surface is Octane/Swoole/RoadRunner on the HTTP path, where the repository is an app singleton across requests. Full mechanism in [pitfalls-deep.md](./references/pitfalls-deep.md).
- Always handle failures -- implement `failed()` on jobs

## Testing (PHPUnit)

### Diagnosing failing tests

1. Run the single failing test in isolation (`phpunit --filter test_name`) before reading app code.
2. Passes solo but fails in the suite → suspect shared state: container singletons, statics, `Carbon::setTestNow()` residue, DB state leaking between tests (the classic paratest failure).
3. Diff expected vs actual output before hypothesizing a cause.
4. Decide explicitly: test-bug or code-bug. Name which before editing either.
5. Never weaken an assertion to make it pass.

`MissingAttributeException` after `create()` usually means strict mode (`Model::shouldBeStrict()`) plus a factory that omits a column with a DB default -- Eloquent never re-reads that default, so the attribute is absent on the instance the factory just built, and the silent case (a rendered instance emitting JSON `null` for a required field) is worse than the thrown one. Fix: set the default on the model (`protected $attributes = [...]`), not the factory. Full mechanism in [testing.md](./references/testing.md).

### Patterns

- **Feature tests** (`tests/Feature/`): HTTP through the full stack (`getJson()`, `postJson()`) -- default for anything touching routes, controllers, or models. **Unit tests** (`tests/Unit/`): isolated services, actions, value objects.
- `RefreshDatabase` for full migration reset per test; `DatabaseTransactions` for transaction-wrap (faster, no migration testing); `DatabaseMigrations` to run and rollback per test
- Model factories for all test data -- never raw `DB::table()` inserts
- One behavior per test. Name with `test_` prefix: `test_user_can_update_own_profile`
- Assert both response status AND side effects (DB state, jobs, notifications): `assertDatabaseHas` / `assertDatabaseMissing`
- `actingAs($user)` for auth, `Sanctum::actingAs($user, ['ability'])` for API auth
- Fake facades BEFORE the action: `Queue::fake()` → act → `Queue::assertPushed(...)`; same for `Http::fake(['host/*' => Http::response(...)])` → `Http::assertSent(...)`
- `Gate::forUser($user)->allows('update', $post)` for authorization assertions
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

Real production footguns, invisible to PHPStan and feature tests alone. Extended mechanics and alternatives in [pitfalls-deep.md](./references/pitfalls-deep.md).

**Query-builder `update()` silently skips observers and audit events.** `Model::query()->where(...)->update([...])` and `Relation::update()` fire no model events -- observers, Auditable traits, `static::saving/updating` all bypassed. Fix: `lockForUpdate() + save()` in a transaction keeps events firing; raw mass update only with a `// intentionally bypasses <Observer>` comment.

**Observer `deleting()` cleanup at parent scope nukes siblings.** `Storage::deleteDirectory($parent->uploadPath)` on a single child delete wipes storage for all siblings while their rows still point at the keys. Detection: when a single-row `delete()` has an Observer, check whether its hooks operate at parent or row scope. Fix: scope cleanup to the row's own paths, or move it to an Action that knows the sibling count.

**`chunkById + json_decode + mutate + json_encode + update` loses concurrent writes on jsonb columns.** Any user save between the SELECT and the per-row UPDATE is silently overwritten. Fix: in-place `DB::raw("jsonb_set(...)")` for shallow edits, or `lockForUpdate()` inside the chunk; the decode/encode default is only safe with writes blocked.

**`date:<fmt>` cast format only reaches `$model->toArray()`, NOT `JsonResource::resolve()`.** A resource returning the raw attribute emits Carbon's ISO 8601, ignoring the cast -- so a cast-format change is not a wire-format change unless the path uses `toArray()` directly (Filament, DTOs, `json_encode($model)`). Verify with a live reproducer before flagging.

**A string that trims to empty skips every non-implicit validation rule.** `" "`, `"\t"`, `""` bypass `array`, `boolean`, `max`, `enum` and every custom rule -- only the implicit set (`required*`, `present*`, `filled`, `accepted*`) still fires. This is a property of the VALUE, not of `nullable`; the `'items.*' => 'array'` guard below stops `{"section": "Bob"}` but not `{"section": " "}`. Fix: normalise blank-ish strings to `null` in `prepareForValidation()`, or `is_array()` at the consumer. Full mechanism in [pitfalls-deep.md](./references/pitfalls-deep.md).

**Nested-array validation accepts scalar elements when only `*.field` rules are set.** `'items.*.name' => 'string'` does not enforce that each `items.*` is an array -- scalars pass, then `$data['items'][0]['name']` yields `null` (blank row) or a `TypeError` (500). Always pair per-key rules with `'items.*' => 'array'`.

**The `boolean` validation rule validates but never normalises.** `1`, `"0"`, etc. all pass, and `validated()` returns them unchanged -- a strict `=== true` compare against accepted input is false, and JSON-bool test payloads never expose it. Fix: cast at the read (`$request->boolean('flag')`, which uses `FILTER_VALIDATE_BOOL`); `boolean:strict` is not a built-in rule. Full mechanism in [pitfalls-deep.md](./references/pitfalls-deep.md).

**`distinct` scopes to the leading explicit path, so at two wildcard levels it compares the whole payload, not per-parent.** `'questions.*.options.*.option_key' => ['distinct']` rejects the same option key reused across two different questions -- `ignore_case`/`strict` change the comparison mode, never the scope. Fix: drop `distinct` and de-dupe per parent in an `after()` closure. Full mechanism in [pitfalls-deep.md](./references/pitfalls-deep.md).

**`Exists` and `Unique` self-skip once the attribute already has a validation message, so `bail` does not protect the query -- the unprotected value is the rule's SCOPE argument, not the attribute.** A malformed UUID never reaches the database; a nullable scope arg cast to `''` against a `uuid` column does (Postgres `22P02`). Triage: is the suspect value the attribute being validated, or an argument to the rule? Full mechanism in [pitfalls-deep.md](./references/pitfalls-deep.md).

**`DB::afterCommit` prevents run-on-rollback but does NOT retry post-commit failures.** Default fix: dispatch a queued job with `tries` + `failed()` that reverts the DB precondition. Alternatives in [pitfalls-deep.md](./references/pitfalls-deep.md).

**Observer writes a model the caller also holds → stale in-memory copy; the caller's later `save()` silently re-clobbers.** Fix: `$model->refresh()` after the triggering event, or `Model::withoutEvents()` when the caller owns the column.

**`BelongsToMany::attach` / `detach` / `sync` / `updateExistingPivot` are query-builder writes -- without `using()`, no pivot model events fire.** Observers and audit traits record nothing. Fix: make the pivot a real `Pivot` model (`->using(PivotModel::class)`) and write through it with `firstOrCreate(...)->fill([...])->save()`. Qualification for one path: `syncWithoutDetaching([$id => [...]])` is attach-or-UPDATE, not insert-only, and `using()` decides both idempotency and whether events fire. It is `sync($ids, false)` -- the `false` disables detaching and nothing else -- and `attachNew()` routes an already-attached id with a non-empty attribute array to `updateExistingPivot()`. Without `using()` that is an unconditional `UPDATE` plus pivot timestamps and no model events, so re-running with the same value still writes. With `using(CustomPivot::class)` it is dirty-checked through `fill()->isDirty()`, issues no query when unchanged, and DOES fire normal Eloquent events on the pivot subclass. "Is it idempotent?" is answered by `grep -n 'using(' <Model>.php`; "does it clobber?" is answered by the pivot column's value set (a two-case enum has nothing to lose; a `draft`/`verified`/`completed` status does).

**`QueryException::getMessage()` interpolates raw query bindings plus host/database into the message** -- any log sink or APM recording exception messages leaks parameter values on every failed query. Recent versions add per-connection `mask_bindings_in_exception_messages` (env `DB_MASK_BINDINGS`), default off; enable in production if query exceptions reach logs (confirm the option exists in the installed version).

**`Carbon::parse('2020')` is today at 20:20, not year 2020** -- a bare 4-digit string parses as `HHMM` time-of-day, breaking date-comparison rules on year-only input. Fix: `Carbon::createFromFormat('Y', $year)->startOfYear()` + partial-date-aware rules. Full mechanism in [pitfalls-deep.md](./references/pitfalls-deep.md).

**A custom auth guard whose failure path calls `report()` can infinitely recurse -- an unauthenticated DoS.** `report()`'s exception context calls `Auth::id()`, which re-enters the same failing guard, which reports again, exhausting memory on a single malformed `Authorization` header. Fix: a `resolving` re-entry flag in the guard, memoising the null resolution. Full mechanism in [pitfalls-deep.md](./references/pitfalls-deep.md).

**A backed enum serialises as the case NAME, never the backing value, so renaming or removing a case breaks unserialization silently rather than raising `Enum::from()`'s `ValueError`.** A removed case degrades to a permanent cache MISS; other shape changes (a new property, a moved class) fail worse and uncaught. Fix: version the cache key whenever a stored object graph's shape changes. Full mechanism in [pitfalls-deep.md](./references/pitfalls-deep.md).

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
- [pitfalls-deep.md](./references/pitfalls-deep.md) -- afterCommit alternatives, observer-desync mechanics, jsonb race, savepoint mechanics
