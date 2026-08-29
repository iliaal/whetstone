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
- **Laravel 12 `route:cache` serializes closure actions instead of throwing `LogicException: Uses Closure`, and a closure that captures `$this` from a service provider recurses infinitely.** `Route::prepareForSerialization()` now hands the action to `SerializableClosure`, which must serialize the bound `$this` -- a provider holds the application container, so serialization never terminates and `route:cache` (and `artisan optimize`, which runs it) exits non-zero with `Maximum call stack size / Infinite recursion?`. Plain closure routes cache fine; group and middleware closures are fine; only serialized ACTION closures matter. Fix: move the handler to an invokable controller, or capture a local `use ($var)` instead of reaching through `$this`. Confirm empirically with `php artisan route:cache; echo $?` with the route present and removed -- grepping for the old exception string finds nothing and reads as a clean bill.

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
- **A custom `CastsAttributes` whose `get()` returns an object is cached and merged BACK through `set()` on the next `save()`.** `getClassCastableAttributeValue()` parks any object return in `$classCastCache` (a `BackedEnum` is an object, so enums qualify), and `Model::save()` opens with `mergeAttributesFromCachedCasts()`. So the tolerant `tryFrom($v) ?? default()` read idiom -- written precisely so an unrecognised stored value degrades during a rolling deploy instead of throwing -- destroys that value: read the attribute, save the model for any unrelated reason, and the unknown string is rewritten as the default. It degrades on read and corrupts on write, in exactly the scenario it exists for. Fix: `public bool $withoutObjectCaching = true;` on the cast. Anything whose job is preserving the stored value -- an audit recorder, a pre-delete snapshot -- must read `getRawOriginal()`, or it records the normalised fallback and the real value is unrecoverable.
- **`Builder::value()` and `pluck()` return the CAST attribute; `DB::table(...)->value()` returns the raw column.** `value()` is `first([$column])` followed by `$result->{$column}`, so the value goes through `getAttribute()` and the cast applies. A guard like `is_string($v) ? Enum::tryFrom($v) : null` therefore returns `null` forever -- no error, no exception, PHPStan clean (`value()` is typed `mixed`, so the narrowing is legal), and green tests, because whatever the guard was meant to reject is now accepted. Accept both shapes: `$v instanceof Enum ? $v : (is_string($v) ? Enum::tryFrom($v) : null)`. The mechanism also fires in reverse -- adding a `$casts` entry for an existing column silently disables every such guard reading it, with no change at any call site for a diff-scoped review to see. When a diff adds a cast, grep every `->value('<column>')` / `->pluck('<column>')` whose result meets `is_string`, `is_int`, a `match`, or a bare `===` against a literal.
- **With `Relation::enforceMorphMap()`, a model missing from the map throws `ClassMorphViolationException` from `getMorphClass()` -- and almost nothing calls `getMorphClass()` on an ordinary `create()` except the audit layer, which is usually config-gated off under test.** So a new model with no map entry passes the entire suite, including tests that create it, and 500s on the first write in an environment where auditing is on. The throw fires inside whatever transaction the write is in, so one unmapped child model rolls back the parent record, its links and any status transition -- the whole request, not just the audit. Add the map entry in the same commit as the model; with `enforceMorphMap` it is part of the class working at all, and overriding an audit-label method is a separate call site that does not substitute. A green suite is not evidence here: check whether the config flag gating the consumer is false under test.

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
- `ShouldBeUnique` interface to prevent duplicate processing -- it is a de-duplication hint, not an at-least-once guarantee. When the lock is already held the dispatch is **silently discarded**: no job queued, no exception, no log line, and `dispatch()` returns normally. Where the skip is user-visible (a re-clicked "regenerate report" that produces nothing), check the lock before dispatching and surface the state. A `Illuminate\Queue\Events\UniqueJobSkipped` event exists on the `13.x` branch but had not landed in a tagged release as of 13.24 -- confirm it is in the installed version before listening for it
- **`WithoutOverlapping` folds the job's class name into the lock key, so two job classes sharing a key do NOT serialize against each other.** `getLockKey()` returns `prefix.get_class($job).':'.$key` unless `->shared()` was called, and `->shared()` is per-middleware-instance -- adding it to only the new job is a no-op, and the remedy therefore has to touch the other job's file. A test asserting `$middleware[0]->key` passes either way, since the public property is equal on both jobs and unaffected by `->shared()`; assert `getLockKey($job)` across both instances, or assert real contention. Changing an already-deployed job's key also opens a rolling-deploy window where old and new workers hold different locks. Before trusting the guarantee at all, check whether the other writer is a job: a synchronous in-request writer takes no queue middleware, so no lock setting can serialize against it.
- **`WithoutOverlapping()->dontRelease()` with no `->expireAfter()` strands the lock on a hard kill.** `expiresAfter` defaults to `0`, which builds a cache lock with no TTL, and the lock is released only in the middleware's `finally` -- SIGKILL, the OOM killer, or a node loss skips it. From then on every job for that key hits the lock-held branch and, because `dontRelease()` set `releaseAfter = null`, falls through both branches and is silently discarded: not run, not retried, not failed, no error surfaced. Any reconciliation command that re-dispatches is discarded too, so the backstop silently no-ops. The knobs are orthogonal -- `dontRelease` = no pile-up, `expireAfter` = self-heal -- and defending one does not address the other. Set a TTL safely longer than the job's worst-case runtime and keep `dontRelease()`.
- **`Context` cannot bleed between queued jobs -- it is flushed and rehydrated from each job's own dispatch payload before `handle()` runs.** `ContextServiceProvider` dehydrates the dispatcher's context into the payload and calls `Context::hydrate()` on `JobProcessing`; `Repository::hydrate()` runs `flush()` first, every time, including when the payload is `null`. So "this job sets Context and never clears it, the next job inherits it" is not a bug. The genuine bleed surface is Octane/Swoole/RoadRunner on the HTTP path, where the repository is an app singleton and a middleware that sets Context for only some requests leaves it set for a later request that does not overwrite it -- a non-issue under PHP-FPM. Within one job Context is shared for the duration, so a handler serving multiple audiences must re-set it per audience.
- Always handle failures -- implement `failed()` on jobs

## Testing (PHPUnit)

### Diagnosing failing tests

1. Run the single failing test in isolation (`phpunit --filter test_name`) before reading app code.
2. Passes solo but fails in the suite → suspect shared state: container singletons, statics, `Carbon::setTestNow()` residue, DB state leaking between tests (the classic paratest failure).
3. Diff expected vs actual output before hypothesizing a cause.
4. Decide explicitly: test-bug or code-bug. Name which before editing either.
5. Never weaken an assertion to make it pass.

Test throws `MissingAttributeException` → strict mode (`Model::shouldBeStrict()`) + factory omits a column with a DB default. Eloquent does not re-read database-level defaults after an INSERT that omitted the column, so the attribute is ABSENT from the instance `create()` returns. The loud failure is the lucky case: `preventAccessingMissingAttributes()` bypasses on `$this->wasRecentlyCreated` in every environment, so a provisioning endpoint that creates the record and renders that same instance in one request emits JSON `null` for the field with nothing thrown, violating a `required` non-nullable OpenAPI field on every such response. The suite cannot reach the silent case: either the factory sets the column, so the attribute exists, or `actingAs()` clears `wasRecentlyCreated` and the read throws. Fix on the model rather than the factory -- `protected $attributes = ['notification_channel' => NotificationChannel::Email]` -- so every creation path carries it; an enum instance is safe as the default, and this does not blunt strict mode, because `newFromBuilder()` calls `setRawAttributes(..., true)` and replaces the defaults wholesale. Adding the column to the factory or `->refresh()` after create fixes only the call site in front of you.

### Patterns

- **Feature tests** (`tests/Feature/`): HTTP through the full stack (`getJson()`, `postJson()`) -- default for anything touching routes, controllers, or models. **Unit tests** (`tests/Unit/`): isolated services, actions, value objects.
- `RefreshDatabase` for full migration reset per test; `DatabaseTransactions` for transaction-wrap (faster, no migration testing); `DatabaseMigrations` to run and rollback per test
- Model factories for all test data -- never raw `DB::table()` inserts
- One behavior per test. Name with `test_` prefix: `test_user_can_update_own_profile`
- Assert both response status AND side effects (DB state, jobs, notifications): `assertDatabaseHas` / `assertDatabaseMissing`
- `actingAs($user)` for auth, `Sanctum::actingAs($user, ['ability'])` for API auth
- Fake facades BEFORE the action: `Queue::fake()` → act → `Queue::assertPushed(...)`; same for `Http::fake(['host/*' => Http::response(...)])` → `Http::assertSent(...)`
- `Gate::forUser($user)->allows('update', $post)` for authorization assertions
- **`Http::assertSent()` passes when ANY recorded request satisfies the callback -- not every request, and not the one you mean.** The common shape, an early `return true` for requests the test does not care about, makes every unrelated request satisfy the whole assertion on its own, so the clause that matters never has to hold. Return `false` for out-of-scope requests, then assert on the single request under test; `assertNotSent` inverts the same way. Prove the assertion is live by mutating the source to violate what it claims to guard and re-running that test alone -- a still-green run means the assertion was never doing anything. Related: after making a straying test hermetic, ask what the live response was doing for the suite; a stray call can be load-bearing coverage, and removing it is a coverage regression disguised as a hygiene fix.
- **`Mail::fake()` records mailables without building them, so `assertSent`/`assertQueued` never compiles the Blade view.** A renamed view variable, a dropped `Content::with()` key, or a `Storage::disk()->url()` on an unconfigured disk all pass CI and throw on the first real send. Force a render: assert on `(new TheMailable(...))->render()`, or call `$mail->assertSeeInHtml(...)` inside the assertion closure, which renders as a side effect. When a mailable or its template changes, confirm at least one test forces a render -- "there is a test for this email" is not "the template compiles".
- **`Mail::fake()` swaps the transport; `Notification::fake()` swaps the whole dispatcher.** Under `Mail::fake()` the notification pipeline still runs -- channels resolve, `send()` executes, and `NotificationSending` / `NotificationSent` fire, so listeners on those events run. Under `Notification::fake()` nothing dispatches and neither event fires. Switching a test from one to the other to use `assertSentTo()` silently stops every `NotificationSent` listener, so an assertion on that listener's side effect either fails or passes vacuously. When a diff moves a side effect onto such a listener, audit every test asserting it: assert what the caller itself sets under the fake, and cover the listener separately by constructing `new NotificationSent(...)` and calling `handle()`.
- **`throttle` middleware reads `config('cache.limiter')`, not `cache.default`, so `Cache::flush()` does not reset rate-limit counters.** With `cache.limiter` hardcoded to a real store, counters go to Redis even when `phpunit.xml` sets `CACHE_STORE=array`, and they accumulate across methods, runs and processes keyed by a constant IP or token -- a later test 429s before reaching its own limit, so the file passes alone and flakes in the suite with "expected 422, received 429". Clear the limiter's own store in `setUp()`: `Cache::store(is_string($s = config('cache.limiter')) ? $s : null)->clear()`. Use `clear()`, not `flush()` (not declared on the `Repository` contract, so PHPStan rejects it), and read the loop bound from the same config the limiter uses instead of a hardcoded literal.
- **`force="true"` on a `phpunit.xml` `<env>` entry pins `getenv()` and `$_ENV`, not Laravel's `env()`.** `PhpHandler::handleEnvVariables()` never writes `$_SERVER`, and phpdotenv's default adapter order puts `ServerConstAdapter` before `EnvConstAdapter` -- so `env()`, and every `config/*.php` that reads it, still resolves the inherited process value. The PHP CLI's default `variables_order=GPCS` is what put that value in `$_SERVER`. The two surfaces have different consumers in one request: `config()` reads `env()`, while an SDK constructed without explicit credentials falls through to its own `getenv()` chain. Pin both; `<server>` is written unconditionally, so `force` on it is redundant rather than required:

  ```xml
  <env name="AWS_ACCESS_KEY_ID" value="testing" force="true"/>
  <server name="AWS_ACCESS_KEY_ID" value="testing"/>
  ```

  A variable that is set but EMPTY is not `false` to `getenv()`, so a non-forced `<env>` entry skips it and the empty value survives the pin.
- **`afterCommit` callbacks DO fire under `RefreshDatabase`** -- the belief that the trait's wrapping transaction defers them forever is false and spreads through test comments justifying weaker assertions. `beginDatabaseTransaction()` installs `Illuminate\Foundation\Testing\DatabaseTransactionsManager`, which skips the wrapping transaction when deciding applicability and runs the callback immediately when no inner transaction is open. So deferral IS testable under the trait: wrap the call in a nested `DB::transaction()` and assert the callback runs on release and is dropped on rollback -- the two cases genuinely differ, so the negative assertion is not vacuous. What is NOT observable under the trait is post-commit DURABILITY: the commit under test is a savepoint. Split the question before choosing (generic form in `ia-writing-tests`).
- **Every parallel worker running `RefreshDatabase` needs its own database, and so does every hand-launched `phpunit`.** `artisan test --parallel` creates `<db>_test_<token>` per worker; a manual fan-out of `vendor/bin/phpunit` processes does not, so concurrent `migrate:fresh` runs race and leave the shared database half-migrated. The signature is schema-level, not assertion-level -- `relation "users" already exists`, `table "cache" does not exist`, `relation "migrations" does not exist` -- in files the change never touched, so it reads as a regression in the code under review. Before launching a suite, confirm no other `phpunit` is running (`ps ax | grep -c '[p]hpunit'`) rather than trusting any external lock; set `DB_DATABASE` per process when runs must overlap. Postgres also needs `max_locks_per_transaction` well above the default 64 -- `migrate:fresh` drops every table in one CASCADE transaction and exhausts the shared lock table around 8 workers. Any other shared store (Redis, an external-store emulator) needs a per-worker prefix or DB index too.
- **`withToken('fake')` sets a header; it does not stub a custom guard.** Mocking the action that ONE middleware uses to turn a token into a user leaves every other path -- a second middleware calling `$request->user()`, exception rendering, audit context -- resolving through the real guard, which will fetch keys over HTTP and decode the fake token for real. Use `actingAs($user, '<guard>')` when the intent is "this request is authenticated", and treat a test that only mocks the resolution action as covering that action, not auth.
- Coverage target: 80%+ with `pcov` or `XDEBUG_MODE=coverage` in CI

Generic test discipline (anti-patterns, mock rules, rationalization resistance): `ia-writing-tests` skill. Laravel testing deep dives: see References below.

## Common Pitfalls

Real production footguns, invisible to PHPStan and feature tests alone. Extended mechanics and alternatives in [pitfalls-deep.md](./references/pitfalls-deep.md).

**Query-builder `update()` silently skips observers and audit events.** `Model::query()->where(...)->update([...])` and `Relation::update()` fire no model events -- observers, Auditable traits, `static::saving/updating` all bypassed. Fix: `lockForUpdate() + save()` in a transaction keeps events firing; raw mass update only with a `// intentionally bypasses <Observer>` comment.

**Observer `deleting()` cleanup at parent scope nukes siblings.** `Storage::deleteDirectory($parent->uploadPath)` on a single child delete wipes storage for all siblings while their rows still point at the keys. Detection: when a single-row `delete()` has an Observer, check whether its hooks operate at parent or row scope. Fix: scope cleanup to the row's own paths, or move it to an Action that knows the sibling count.

**`chunkById + json_decode + mutate + json_encode + update` loses concurrent writes on jsonb columns.** Any user save between the SELECT and the per-row UPDATE is silently overwritten. Fix: in-place `DB::raw("jsonb_set(...)")` for shallow edits, or `lockForUpdate()` inside the chunk; the decode/encode default is only safe with writes blocked.

**`date:<fmt>` cast format only reaches `$model->toArray()`, NOT `JsonResource::resolve()`.** A resource returning the raw attribute emits Carbon's ISO 8601, ignoring the cast -- so a cast-format change is not a wire-format change unless the path uses `toArray()` directly (Filament, DTOs, `json_encode($model)`). Verify with a live reproducer before flagging.

**A string that trims to empty skips every non-implicit validation rule.** `Validator::presentOrRuleIsImplicit` short-circuits on `is_string($value) && trim($value) === ''`, so `" "`, `"\t"`, `"\n"`, `""` bypass `array`, `boolean`, `string`, `max`, `enum` and every custom `ValidationRule` -- only the implicit set (`required*`, `present*`, `missing*`, `filled`, `accepted*`, `declined*`) still fires. This is a property of the VALUE, not of `nullable`. So the `'items.*' => 'array'` guard below stops `{"section": "Bob"}` with a 422 and does not stop `{"section": " "}`, which slips past `empty()` too and reaches a handler type-hinted `array` as a `TypeError`. Fix: normalise blank-ish strings to `null` in `prepareForValidation()`, or `is_array()` at the consumer -- adding another rule does nothing, it is skipped for the same reason. Never conclude "the array rule protects this" from a non-blank-scalar 422.

**Nested-array validation accepts scalar elements when only `*.field` rules are set.** `'items.*.name' => 'string'` does not enforce that each `items.*` is an array -- scalars pass, then `$data['items'][0]['name']` yields `null` (blank row) or a `TypeError` (500). Always pair per-key rules with `'items.*' => 'array'`.

**The `boolean` validation rule validates but never normalises.** `1`, `0`, `"1"`, `"0"` all pass, and `validated()` / `input()` return them unchanged, so `$validated['flag'] === true` is false for input the rule accepted -- and a strict compare against a stored default then persists a spurious override that never clears. Test payloads written with real JSON `true`/`false` decode to PHP bools and never expose it. Fix: cast at the read (`(bool) $validated['flag']`) or use `$request->boolean('flag')`, which does cast via `FILTER_VALIDATE_BOOL`. `boolean:strict` is not a built-in rule.

**`distinct` scopes to the leading explicit path, so at two wildcard levels it compares the whole payload.** `'questions.*.options.*.option_key' => ['distinct']` reads as "unique within each question" and is not: `getLeadingExplicitAttributePath()` returns everything before the first asterisk (`questions`), and that subtree is flattened with `Arr::dot()`, so two different questions carrying the same option key are both rejected. `ignore_case` and `strict` change the comparison mode, never the scope; there is no per-parent option. The idiom is correct at one wildcard and silently changes meaning at two. Fix: drop `distinct` and de-dupe per parent in an `after()` closure, flagging every member of a colliding group rather than only the later one, so existing `assertJsonValidationErrors` paths still resolve.

**`Exists` and `Unique` self-skip once the attribute has any message; the unprotected value is the one baked into the rule's SCOPE.** `hasNotFailedPreviousRuleIfPresenceRule` gates exactly those two rules on `! $this->messages->has($attribute)`, so `['uuid', Rule::exists(...)]` cannot send a malformed UUID to the database, and adding `bail` changes nothing. The real 500 comes from the other side: `Rule::exists('docs', 'id')->where('owner_id', (string) $user->owner?->id)` casts `null` to `''` and compares it against a `uuid` column (Postgres `22P02`). Passing the nullable value through unchanged routes to `whereNull()` and yields a clean 422. Triage discriminator: is the suspect value the attribute being validated, or an argument to the rule? Only the second is exposed.

**`DB::afterCommit` prevents run-on-rollback but does NOT retry post-commit failures.** Default fix: dispatch a queued job with `tries` + `failed()` that reverts the DB precondition. Alternatives in [pitfalls-deep.md](./references/pitfalls-deep.md).

**Observer writes a model the caller also holds → stale in-memory copy; the caller's later `save()` silently re-clobbers.** Fix: `$model->refresh()` after the triggering event, or `Model::withoutEvents()` when the caller owns the column.

**`BelongsToMany::attach` / `detach` / `sync` / `updateExistingPivot` are query-builder writes -- without `using()`, no pivot model events fire.** Observers and audit traits record nothing. Fix: make the pivot a real `Pivot` model (`->using(PivotModel::class)`) and write through it with `firstOrCreate(...)->fill([...])->save()`. Qualification for one path: `syncWithoutDetaching([$id => [...]])` is attach-or-UPDATE, not insert-only, and `using()` decides both idempotency and whether events fire. It is `sync($ids, false)` -- the `false` disables detaching and nothing else -- and `attachNew()` routes an already-attached id with a non-empty attribute array to `updateExistingPivot()`. Without `using()` that is an unconditional `UPDATE` plus pivot timestamps and no model events, so re-running with the same value still writes. With `using(CustomPivot::class)` it is dirty-checked through `fill()->isDirty()`, issues no query when unchanged, and DOES fire normal Eloquent events on the pivot subclass. "Is it idempotent?" is answered by `grep -n 'using(' <Model>.php`; "does it clobber?" is answered by the pivot column's value set (a two-case enum has nothing to lose; a `draft`/`verified`/`completed` status does).

**`QueryException::getMessage()` interpolates raw query bindings plus host/database into the message** -- any log sink or APM recording exception messages leaks parameter values on every failed query. Recent versions add per-connection `mask_bindings_in_exception_messages` (env `DB_MASK_BINDINGS`), default off; enable in production if query exceptions reach logs (confirm the option exists in the installed version).

**`Carbon::parse('2020')` is today at 20:20, not year 2020** -- a bare 4-digit string parses as `HHMM` time-of-day, breaking `before_or_equal:today` / `after` / `before` on year-only input. Fix: `Carbon::createFromFormat('Y', $year)->startOfYear()` + partial-date-aware rules; when migrating a field's validator type, audit its sibling validators for the same incompatibility.

**A custom auth guard whose failure path calls `report()` infinitely recurses, and it is an unauthenticated DoS.** Laravel's exception-report context calls `Auth::id()`, which re-enters the same guard mid-resolution, which fails again and reports again: `user() -> catch (Throwable) -> report() -> Handler::context() -> Auth::id() -> user()`. Any middleware calling `$request->user()` on such a route turns a malformed `Authorization: Bearer <garbage>` into an OOM'd worker. It presents as an HTTP-client or JWT-library bug because the fatal crash site moves between runs -- memory is already exhausted, so whichever allocation comes next dies; faking the outbound call just relocates the OOM downstream of the real consumer. Fix in the guard: a `resolving` flag returning `null` on re-entry, plus memoising the null resolution so repeated `user()` calls do not re-run the whole fetch-and-decode. Any resolver whose failure path calls `report()`, logs with auth context, or fires an event touching `Auth::user()` is a candidate.

**A backed enum serialises as `E:<len>:"<FQCN>:<CaseName>"` -- the case NAME, never the backing value -- so reordering cases is serialization-safe and renaming or removing one is not.** Unserializing a removed case emits a warning and returns `false`; it does NOT raise `Enum::from()`'s `ValueError: X is not a valid backing value`, which is the message people write from memory into comments and MR descriptions. Under Laravel's `HandleExceptions` that warning becomes an `ErrorException`, so a `catch (Throwable)` decoder absorbs it and the entry degrades to a permanent MISS -- one rebuild plus one `report()` per read for the rest of its TTL. The other two shapes are worse because nothing catches them: a newly added promoted property unserializes fine and fires an `Error` at the consumer's first read, and a renamed or moved class warns not at all and serves `__PHP_Incomplete_Class` as a clean HIT. Version the cache key whenever a stored object graph's shape changes.

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
