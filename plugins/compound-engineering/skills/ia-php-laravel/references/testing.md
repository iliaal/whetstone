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
./vendor/bin/phpunit --processes=auto              # parallel (PHPUnit 11+)
./vendor/bin/phpunit --coverage-text --min=80      # with coverage threshold

php artisan test                                   # small suites or quick runs
php -d memory_limit=1G artisan test                # if artisan needed on large suites
```
