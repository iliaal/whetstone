# Testing Laravel (PHPUnit)

Use PHPUnit with Laravel's testing helpers. Every test file starts with `declare(strict_types=1)`.

## PHPUnit Essentials

```php
<?php

declare(strict_types=1);

namespace Tests\Feature;

use App\Models\{User, Post};
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

final class PostTest extends TestCase
{
    use RefreshDatabase;

    public function test_authenticated_user_can_create_post(): void
    {
        $user = User::factory()->create();

        $response = $this->actingAs($user)
            ->postJson('/api/posts', ['title' => 'New Post', 'body' => 'Content']);

        $response->assertCreated()
            ->assertJson(['data' => ['title' => 'New Post']]);

        $this->assertDatabaseHas('posts', [
            'title' => 'New Post',
            'user_id' => $user->id,
        ]);
    }
}
```

## Data Providers

Data providers for boundary/validation testing:

```php
#[DataProvider('titleLengthProvider')]
public function test_validates_title_length(string $title, bool $valid): void
{
    $user = User::factory()->create();
    $response = $this->actingAs($user)
        ->postJson('/api/posts', ['title' => $title, 'body' => 'Content']);

    $valid ? $response->assertCreated() : $response->assertUnprocessable();
}

public static function titleLengthProvider(): array
{
    return [
        'too short' => ['AB', false],
        'minimum valid' => ['ABC', true],
        'maximum valid' => [str_repeat('A', 255), true],
        'too long' => [str_repeat('A', 256), false],
    ];
}
```

## Running Tests

For large test suites, call PHPUnit directly to avoid artisan's memory overhead:

```bash
./vendor/bin/phpunit                              # all tests (direct, lower memory)
./vendor/bin/phpunit --filter=PostTest             # by name
./vendor/bin/paratest --processes=auto   # parallel via ParaTest (what artisan test --parallel wraps)
./vendor/bin/phpunit --coverage-text --min=80      # with coverage threshold

php artisan test                                   # small suites or quick runs
php -d memory_limit=1G artisan test                # if artisan needed on large suites
```

## Strict-mode MissingAttributeException from factories

Test throws `MissingAttributeException` → strict mode (`Model::shouldBeStrict()`) + factory omits a column with a DB default. Eloquent does not re-read database-level defaults after an INSERT that omitted the column, so the attribute is ABSENT from the instance `create()` returns. The loud failure is the lucky case: `preventAccessingMissingAttributes()` bypasses on `$this->wasRecentlyCreated` in every environment, so a provisioning endpoint that creates the record and renders that same instance in one request emits JSON `null` for the field with nothing thrown, violating a `required` non-nullable OpenAPI field on every such response. The suite cannot reach the silent case: either the factory sets the column, so the attribute exists, or `actingAs()` clears `wasRecentlyCreated` and the read throws. Fix on the model rather than the factory -- `protected $attributes = ['notification_channel' => NotificationChannel::Email]` -- so every creation path carries it; an enum instance is safe as the default, and this does not blunt strict mode, because `newFromBuilder()` calls `setRawAttributes(..., true)` and replaces the defaults wholesale. Adding the column to the factory or `->refresh()` after create fixes only that one call site.

## Environment variable pinning in phpunit.xml

`force="true"` on a `phpunit.xml` `<env>` entry pins `getenv()` and `$_ENV`, not Laravel's `env()`. `PhpHandler::handleEnvVariables()` never writes `$_SERVER`, and phpdotenv's default adapter order puts `ServerConstAdapter` before `EnvConstAdapter` -- so `env()`, and every `config/*.php` that reads it, still resolves the inherited process value. The PHP CLI's default `variables_order=GPCS` is what put that value in `$_SERVER`. The two surfaces have different consumers in one request: `config()` reads `env()`, while an SDK constructed without explicit credentials falls through to its own `getenv()` chain. Pin both; `<server>` is written unconditionally, so `force` on it is redundant rather than required:

```xml
<env name="AWS_ACCESS_KEY_ID" value="testing" force="true"/>
<server name="AWS_ACCESS_KEY_ID" value="testing"/>
```

A variable that is set but EMPTY is not `false` to `getenv()`, so a non-forced `<env>` entry skips it and the empty value survives the pin.

## afterCommit callbacks under RefreshDatabase

`afterCommit` callbacks DO fire under `RefreshDatabase` -- the belief that the trait's wrapping transaction defers them forever is false and spreads through test comments justifying weaker assertions. `beginDatabaseTransaction()` installs `Illuminate\Foundation\Testing\DatabaseTransactionsManager`, which skips the wrapping transaction when deciding applicability and runs the callback immediately when no inner transaction is open. So deferral IS testable under the trait: wrap the call in a nested `DB::transaction()` and assert the callback runs on release and is dropped on rollback -- the two cases genuinely differ, so the negative assertion is not vacuous. What is NOT observable under the trait is post-commit DURABILITY: the commit under test is a savepoint. Split the question before choosing (generic form in `ia-writing-tests`).

## Parallel worker database isolation

Every parallel worker running `RefreshDatabase` needs its own database, and so does every hand-launched `phpunit`. `artisan test --parallel` creates `<db>_test_<token>` per worker; a manual fan-out of `vendor/bin/phpunit` processes does not, so concurrent `migrate:fresh` runs race and leave the shared database half-migrated. The signature is schema-level, not assertion-level -- `relation "users" already exists`, `table "cache" does not exist`, `relation "migrations" does not exist` -- in files the change never touched, so it reads as a regression in the code under review. Before launching a suite, confirm no other `phpunit` is running (`ps ax | grep -c '[p]hpunit'`) rather than trusting any external lock; set `DB_DATABASE` per process when runs must overlap. Postgres also needs `max_locks_per_transaction` well above the default 64 -- `migrate:fresh` drops every table in one CASCADE transaction and exhausts the shared lock table around 8 workers. Any other shared store (Redis, an external-store emulator) needs a per-worker prefix or DB index too.

## withToken() does not stub a custom guard

`withToken('fake')` sets a header; it does not stub a custom guard. Mocking the action that ONE middleware uses to turn a token into a user leaves every other path -- a second middleware calling `$request->user()`, exception rendering, audit context -- resolving through the real guard, which will fetch keys over HTTP and decode the fake token for real. Use `actingAs($user, '<guard>')` when the intent is "this request is authenticated", and treat a test that only mocks the resolution action as covering that action, not auth.
