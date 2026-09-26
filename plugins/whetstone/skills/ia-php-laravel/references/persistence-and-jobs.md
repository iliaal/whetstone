# Persistence and job patterns

## Migrations

- Anonymous class migrations; `snake_case` plural table names matching model convention
- Foreign keys: `$table->foreignId('user_id')->constrained()->cascadeOnDelete()`. Always index foreign keys and frequently filtered columns.
- Down method: rollback logic or `Schema::dropIfExists()` for new tables
- Separate schema and data migrations: backfills in their own migration file, not mixed with DDL. One deliberate exception: when a single transaction is what closes a rolling-deploy null window, splitting reopens it; the lock-duration trade-off and table-size disposition live in the `ia-postgresql` skill, Migration Safety
- Renames/removals use expand-contract: add new column → backfill → switch reads → drop old (full pattern in `ia-postgresql` skill)
- Never edit a migration that has run in a shared environment; write a new one
- **Set `public $withinTransaction = false;` for per-row commit/lock-release (resumable backfills) or statements Postgres rejects inside a transaction (`CREATE INDEX CONCURRENTLY`, `ALTER TYPE ... ADD VALUE`).** Otherwise inner `DB::transaction()` loops become savepoints, not independent commits ([pitfalls-deep.md](./pitfalls-deep.md)); no-op on MySQL.
- **The `migrations` row is inserted AFTER `up()` returns and outside its transaction**, so a process killed in that window leaves a committed-but-unrecorded migration and every later container re-runs `up()` into `relation already exists`, a crash loop that bricks all further deploys. Fix: an early-return `Schema::hasTable()` guard at the top of `up()`. Full mechanism in [common-pitfalls.md](./common-pitfalls.md).
- `migrate:fresh` resets only the SQL connection; external stores (DynamoDB, S3, Redis) persist across it, so external-store data migrations re-run on already-migrated data and must be idempotent on a second run.


## Eloquent

- `Model::preventLazyLoading(!app()->isProduction())` catches N+1 during development
- Select only needed columns: `Post::with(['user:id,name'])->select(['id', 'title', 'user_id'])`
- Bulk operations at database level: `Post::where('status', 'draft')->update([...])`; never load into memory to update. `increment()`/`decrement()` for counters.
- Composite indexes for common query combinations
- `chunk(1000)` for large datasets, lazy collections for memory-constrained processing
- Query scopes (`scopeActive`, `scopeRecent`) for reusable constraints
- `withCount('comments')` / `withExists('approvals')`; never load relations just to count
- `->when($filter, fn($q) => $q->where(...))` for conditional query building
- `DB::transaction(fn() => ...)` gives automatic rollback on exception
- `Model::upsert($rows, ['unique_key'], ['update_cols'])` for bulk insert-or-update
- **`updateOrCreate($match, $values)` reassigns the primary key on the update branch when `$values` carries a fillable identity column.** On the second call Eloquent runs `fill($values)->save()` and the WHERE uses the ORIGINAL key, so the row's id churns on every redelivery, the opposite of the idempotency intended. Fix: keep `id` out of `$values`. Full mechanism in [pitfalls-deep.md](./pitfalls-deep.md).
- `Prunable` / `MassPrunable` with `prunable()` query for automatic stale record cleanup
- `$guarded = []` is a mass assignment vulnerability; always explicit `$fillable`
- **A custom `CastsAttributes` whose `get()` returns an object is cached and merged BACK through `set()` on the next `save()`,** so a tolerant `tryFrom($v) ?? default()` read idiom overwrites the original stored value on any unrelated save. Fix: `public bool $withoutObjectCaching = true;` on the cast; anything preserving the stored value must read `getRawOriginal()`. Full mechanism in [pitfalls-deep.md](./pitfalls-deep.md).
- **`Builder::value()` and `pluck()` return the CAST attribute; `DB::table(...)->value()` returns the raw column.** A guard like `is_string($v) ? Enum::tryFrom($v) : null` silently returns `null` forever once a `$casts` entry exists: no error, clean PHPStan, green tests. Grep every `->value()`/`->pluck()` when a diff adds a cast. Full mechanism in [pitfalls-deep.md](./pitfalls-deep.md).
- **With `Relation::enforceMorphMap()`, a model missing from the map throws `ClassMorphViolationException` from the audit layer, which is usually config-gated off under test**, so a new unmapped model passes the whole suite and 500s on the first audited write. The read side is the mirror: every morph write stores the ALIAS, so a hardcoded `where('<rel>_type', 'App\\Models\\Foo')` matches zero rows; use `(new Foo)->getMorphClass()`. Full mechanism in [pitfalls-deep.md](./pitfalls-deep.md).
- **`latest()` / `orderByDesc()` on a relation that already declares an order APPENDS to it.** `hasMany(Version::class)->orderBy('created_at')` plus `->latest('created_at')->first()` compiles to `ORDER BY created_at asc, created_at desc` and returns the oldest row; a single-row fixture masks it. Fix: `reorder('created_at', 'desc')`, or a dedicated `latestVersion(): HasOne`. Full mechanism in [pitfalls-deep.md](./pitfalls-deep.md).


## Queues & Jobs

- Batching: `Bus::batch([...])->then()->catch()->finally()->dispatch()`; chaining: `Bus::chain([new Step1, new Step2])->dispatch()`
- Rate limiting: `Redis::throttle('api')->allow(10)->every(60)->then(fn() => ...)`
- Central routing (Laravel 13): `Queue::route(ProcessPodcast::class, connection: 'redis', queue: 'podcasts')` in a service provider's `boot()` replaces scattered `$connection`/`$queue` properties; the first argument may also be an interface, trait, or parent class, and an array form routes many classes at once. The route is a default only: a per-job `$connection`/`$queue` value (property, or set through `onQueue()`/`onConnection()`) is read first and wins. `Queue::forward('reports', 'reports.fifo', 'sqs')` re-targets an existing queue name without touching jobs or dispatch sites.
- **`ShouldBeUnique` prevents duplicate processing; it is a de-duplication hint, not an at-least-once guarantee.** When the lock is already held, dispatch is silently discarded: no job, no exception, no log line. Fix: check the lock before dispatching where the skip is user-visible; confirm `UniqueJobSkipped` exists in the installed version before relying on it. Full mechanism in [pitfalls-deep.md](./pitfalls-deep.md).
- **`WithoutOverlapping` folds the job's class name into the lock key, so two job classes sharing a key do NOT serialize against each other** unless both call `->shared()`. A synchronous in-request writer takes no queue middleware, so no lock setting can serialize against it either. Fix: assert real contention (`getLockKey()` across both instances), not the middleware's public property. Full mechanism in [pitfalls-deep.md](./pitfalls-deep.md).
- **`WithoutOverlapping()->dontRelease()` with no `->expireAfter()` strands the lock forever on a hard kill (SIGKILL, OOM, node loss).** Every subsequent job for that key is then silently discarded, including from a reconciliation command. Fix: set a TTL safely longer than the job's worst-case runtime and keep `dontRelease()`; the two knobs are orthogonal. Full mechanism in [pitfalls-deep.md](./pitfalls-deep.md).
- **`Context` cannot bleed between queued jobs: it is flushed and rehydrated from each job's own dispatch payload before `handle()` runs.** The genuine bleed surface is Octane/Swoole/RoadRunner on the HTTP path, where the repository is an app singleton across requests. Full mechanism in [pitfalls-deep.md](./pitfalls-deep.md).
- **Adding a constructor parameter to a `ShouldQueue` job breaks every payload already queued, and a promoted default does not save it**: `unserialize()` skips the constructor and restores only declaration-level defaults, which a promoted (or `readonly`) property has none of. Fix: a plain property with a declaration-level default, assigned in the constructor body, set to what an already-enqueued payload MEANT. Full mechanism in [pitfalls-deep.md](./pitfalls-deep.md).
- **A connection's `retry_after` must exceed the longest job `$timeout` / worker `--timeout`, or a job still running is handed to a second worker.** On the `database`, `redis`, and `beanstalkd` drivers a reserved job whose reservation is older than `retry_after` goes back on the queue whether or not its worker finished; the shipped `config/queue.php` sets 90s (the `database` and `redis` connectors fall back to 60s when the key is absent), so any job allowed to run longer is exposed. Keep the worker `--timeout` a few seconds under `retry_after`. SQS uses the queue's visibility timeout instead. Correct timeouts still do not replace idempotency: a worker can die after the side effect and before the delete.
- Always handle failures: implement `failed()` on jobs


## Production Resilience

- **Fail-fast config validation** in a service provider's `boot()`: missing API keys, invalid DSNs, misconfigured queues crash on startup, not on the first request that hits the code path.
- **Health endpoints**: `/health` (shallow, 200 if the process responds) and `/ready` (deep: checks DB, Redis, critical services).
- **A `set -e` container entrypoint is a fail-fast contract; only put steps there whose failure should genuinely block traffic.** Migrations and `config:cache` qualify; docs generation and optional caches do not, because their non-zero exit aborts the boot before php-fpm and the workers start. Full mechanism in [common-pitfalls.md](./common-pitfalls.md).
- **`Redis::pipeline()` and `Redis::transaction()` historically did not carry the reconnect-and-retry that plain `Redis::` commands have.** A connection lost across a Redis failover or restart during a pipeline or `MULTI` block leaves the connection object broken, so every later pipeline or transaction on that instance keeps failing until the process restarts, while ordinary commands on the same facade reconnect and recover, which makes the failure look intermittent and command-specific. Anything batching Redis work (bulk cache writes, rate limiters, queue metrics) must either confirm the installed framework version carries pipeline-level retry (the fix is recent; read `Illuminate\Redis\Connections\PhpRedisConnection::pipeline()` / `transaction()` in `vendor/`, do not assume from the changelog) or wrap the batch in its own catch-reconnect-retry path (`Redis::purge($name)` then re-run the batch once). Long-lived processes (`queue:work`, Octane, Horizon) are the exposed ones; PHP-FPM hides it because the next request gets a fresh connection.


## Production Performance

OPcache + JIT + preloading configuration and Laravel deploy caches (`config:cache`, `route:cache`, etc.): [production-performance.md](./production-performance.md)
