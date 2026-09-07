# Testing and pitfall checklist

## Testing (PHPUnit)

### Diagnosing failing tests

1. Run the single failing test in isolation (`phpunit --filter test_name`) before reading app code.
2. Passes solo but fails in the suite → suspect shared state: container singletons, statics, `Carbon::setTestNow()` residue, DB state leaking between tests. A `private static` memo is the sharp case -- process-scoped, so no rollback reaches it; reset it through reflection rather than deleting it ([testing.md](./testing.md)).
3. Diff expected vs actual output before hypothesizing a cause.
4. Decide explicitly: test-bug or code-bug. Name which before editing either.
5. Never weaken an assertion to make it pass.

`MissingAttributeException` after `create()` usually means strict mode (`Model::shouldBeStrict()`) plus a factory omitting a column with a DB default -- Eloquent never re-reads that default. The silent case (a freshly created instance rendering JSON `null` for a required field) is worse than the thrown one. Fix on the model (`protected $attributes = [...]`), not the factory. Full mechanism in [testing.md](./testing.md).

### Patterns

- **Feature tests** (`tests/Feature/`): HTTP through the full stack (`getJson()`, `postJson()`) -- default for anything touching routes, controllers, or models. **Unit tests** (`tests/Unit/`): isolated services, actions, value objects.
- `RefreshDatabase` for full migration reset per test; `DatabaseTransactions` for transaction-wrap (faster, no migration testing); `DatabaseMigrations` to run and rollback per test
- Model factories for all test data -- never raw `DB::table()` inserts
- **Factories build the model inside `Model::unguarded()`, so a fixture can set a column `$fillable` rejects** -- the test then pins a row shape the runtime cannot produce, not merely one it does not. Fix: diff the factory payload's keys against `$fillable` before reading a guard test as coverage. Full mechanism in [factories.md](./factories.md).
- One behavior per test. Name with `test_` prefix: `test_user_can_update_own_profile`
- Assert both response status AND side effects (DB state, jobs, notifications): `assertDatabaseHas` / `assertDatabaseMissing`
- `actingAs($user)` for auth, `Sanctum::actingAs($user, ['ability'])` for API auth
- Fake facades BEFORE the action: `Queue::fake()` → act → `Queue::assertPushed(...)`; same for `Http::fake(['host/*' => Http::response(...)])` → `Http::assertSent(...)`
- `Gate::forUser($user)->allows('update', $post)` for authorization assertions
- **`assertJsonValidationErrors(['field'])` passes on ANY error for that field**, so an earlier rule in the chain -- or a service-layer `ValidationException::withMessages()` on the same key -- satisfies a test named for the rule under test. Fix: assert the message form (`['field' => 'must not be greater than']`) and delete the rule to prove which guard answered. Full mechanism in [feature-testing.md](./feature-testing.md).
- **Mockery cannot mock a `readonly` class** -- it generates a non-readonly subclass, which PHP 8.2+ rejects at class-load time, so the file dies with a FATAL (not a catchable exception) before any assertion runs. Fix: construct the real object (DTOs are free) or mock an interface it implements. Full mechanism in [mocking-and-faking.md](./mocking-and-faking.md).
- **`Http::assertSent()` passes when ANY recorded request satisfies the callback -- not every request, and not necessarily the one under test.** An early `return true` for out-of-scope requests makes every unrelated request satisfy the whole assertion on its own. Fix: return `false` for out-of-scope requests, then assert on the single request under test. Full mechanism in [mocking-and-faking.md](./mocking-and-faking.md).
- **`Mail::fake()` records mailables without building them, so `assertSent`/`assertQueued` never compiles the Blade view** -- a broken template still passes CI. Fix: force a render (`(new TheMailable(...))->render()` or `assertSeeInHtml()`) in at least one test per mailable. Full mechanism in [mocking-and-faking.md](./mocking-and-faking.md).
- **`Mail::fake()` swaps only the transport (the notification pipeline still runs); `Notification::fake()` swaps the whole dispatcher and neither `NotificationSending` nor `NotificationSent` fires.** Switching fakes to reach `assertSentTo()` silently kills listeners on those events. Fix: audit and cover those listeners separately. Full mechanism in [mocking-and-faking.md](./mocking-and-faking.md).
- **`throttle` middleware reads `config('cache.limiter')`, not `cache.default`, so `Cache::flush()` does not reset rate-limit counters** and tests can flake in the suite while passing alone. Fix: clear the limiter's own store in `setUp()` (`Cache::store(config('cache.limiter'))->clear()`). Full mechanism in [mocking-and-faking.md](./mocking-and-faking.md).
- **`force="true"` on a `phpunit.xml` `<env>` entry pins `getenv()`/`$_ENV`, not Laravel's `env()`** -- both surfaces need pinning because `config()` reads `env()` while a raw SDK falls through to its own `getenv()` chain. Fix: set both `<env force="true">` and `<server>` entries. Full mechanism in [testing.md](./testing.md).
- **`afterCommit` callbacks DO fire under `RefreshDatabase`** -- the belief they're deferred forever is false, but post-commit DURABILITY still isn't observable since the commit under test is a savepoint. Fix: test deferral behavior directly; verify durability claims separately. Full mechanism in [testing.md](./testing.md).
- **Every parallel worker running `RefreshDatabase` needs its own database** -- `artisan test --parallel` provisions one per worker, a manual `phpunit` fan-out does not, and concurrent `migrate:fresh` races leave the shared DB half-migrated. Fix: confirm no other `phpunit` process is running before launching a suite; set `DB_DATABASE` per process for intentional overlap. Full mechanism (including Postgres `max_locks_per_transaction`) in [testing.md](./testing.md).
- **`withToken('fake')` sets a header; it does not stub a custom guard**, so every other path still resolves through the real guard. Fix: use `actingAs($user, '<guard>')` when the intent is "this request is authenticated". Full mechanism in [testing.md](./testing.md).
- Coverage target: 80%+ with `pcov` or `XDEBUG_MODE=coverage` in CI

Generic test discipline (anti-patterns, mock rules, rationalization resistance): `ia-writing-tests` skill. Laravel testing deep dives: see References below.


## Common Pitfalls

Real production footguns, invisible to PHPStan and feature tests alone. Mechanism and fix for each: [common-pitfalls.md](./common-pitfalls.md), except where the bullet links elsewhere.

- **Query-builder `update()`** -- `Model::query()->where(...)->update([...])` and `Relation::update()` fire no model events, so observers and audit traits are bypassed.
- **A database-level FK cascade** -- fires no Eloquent events, and is a pure no-op when the parent uses `SoftDeletes`, because the trait rewrites `delete()` as an `UPDATE`.
- **Observer `deleting()` cleanup at parent scope** -- wipes every sibling's storage on a single-row delete.
- **`BelongsToMany` pivot writes** -- `attach`/`detach`/`sync`/`updateExistingPivot` fire no pivot model events without `using()`, and `sync()` reads the RAW pivot table, so a relationship-level `where` never filters it.
- **`chunkById + json_decode + mutate + json_encode + update`** -- loses any concurrent write to a jsonb column between the SELECT and the UPDATE ([pitfalls-deep.md](./pitfalls-deep.md)).
- **`date:<fmt>` cast format** -- reaches `$model->toArray()` only, never `JsonResource::resolve()`.
- **A string that trims to empty** -- skips every non-implicit validation rule, `nullable` or not ([pitfalls-deep.md](./pitfalls-deep.md)).
- **An empty array versus an absent key** -- indistinguishable through `empty()`, `?? null` and `isset()`, so a Clear-all save is a silent no-op; form encoding drops it on the wire too.
- **Nested-array validation** -- `'items.*.name'` rules do not stop `items.*` from being a scalar; always pair with `'items.*' => 'array'`.
- **`validated()`** -- rebuilds a nested key from its ruled sub-keys only and drops the rest ([pitfalls-deep.md](./pitfalls-deep.md)).
- **The `boolean` rule** -- validates but never normalises, so `=== true` is false for input it accepted ([pitfalls-deep.md](./pitfalls-deep.md)).
- **`distinct` at two wildcard levels** -- compares the whole payload, not per-parent ([pitfalls-deep.md](./pitfalls-deep.md)).
- **`Exists` / `Unique` self-skip after any message** -- so `bail` does not protect the query, and the exposed value is the rule's SCOPE argument ([pitfalls-deep.md](./pitfalls-deep.md)).
- **`DB::afterCommit`** -- prevents run-on-rollback; it does NOT retry a post-commit failure ([pitfalls-deep.md](./pitfalls-deep.md)).
- **An observer writing a model the caller also holds** -- leaves a stale in-memory copy that the caller's later `save()` re-clobbers ([pitfalls-deep.md](./pitfalls-deep.md)).
- **`Collection::unique()`** -- compares loosely, so `"00123"` and `"123"` collapse and a dedup or merge guard silently drops data; use `uniqueStrict()`.
- **`QueryException::getMessage()`** -- interpolates raw bindings plus host and database into the message.
- **`Carbon::parse('2020')`** -- is today at 20:20, not the year 2020 ([pitfalls-deep.md](./pitfalls-deep.md)).
- **A custom auth guard whose failure path calls `report()`** -- infinitely recurses; an unauthenticated DoS ([pitfalls-deep.md](./pitfalls-deep.md)).
- **A backed enum serialises as the case NAME** -- so renaming or removing a case breaks unserialization silently ([pitfalls-deep.md](./pitfalls-deep.md)).
- **A `composer.lock` conflict confined to `content-hash`** -- is not a lock conflict; recompute it, never hand-pick a side ([pitfalls-deep.md](./pitfalls-deep.md)).
