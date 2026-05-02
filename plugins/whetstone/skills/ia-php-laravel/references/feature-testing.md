# Feature Testing Patterns

## Authentication Testing

```php
public function test_authenticated_user_can_access_endpoint(): void
{
    $user = User::factory()->create();

    $this->actingAs($user)
        ->getJson('/api/profile')
        ->assertOk()
        ->assertJson(['data' => ['id' => $user->id]]);
}

public function test_guest_receives_401(): void
{
    $this->getJson('/api/profile')->assertUnauthorized();
}

// Sanctum with specific abilities
public function test_user_with_wrong_ability_gets_403(): void
{
    $user = User::factory()->create();
    Sanctum::actingAs($user, ['view-posts']);

    $this->postJson('/api/posts', ['title' => 'Test'])
        ->assertForbidden();
}
```

## Authorization Testing

```php
public function test_user_cannot_delete_others_posts(): void
{
    $user = User::factory()->create();
    $post = Post::factory()->create(); // different user

    $this->actingAs($user)
        ->deleteJson("/api/posts/{$post->id}")
        ->assertForbidden();
}

public function test_admin_can_delete_any_post(): void
{
    $admin = User::factory()->admin()->create();
    $post = Post::factory()->create();

    $this->actingAs($admin)
        ->deleteJson("/api/posts/{$post->id}")
        ->assertNoContent();

    $this->assertDatabaseMissing('posts', ['id' => $post->id]);
}
```

## Validation Testing

```php
public function test_post_requires_title_and_content(): void
{
    $user = User::factory()->create();

    $this->actingAs($user)
        ->postJson('/api/posts', [])
        ->assertUnprocessable()
        ->assertJsonValidationErrors(['title', 'content']);
}
```

## API Response Structure

```php
public function test_returns_paginated_posts(): void
{
    Post::factory()->count(30)->create();

    $this->getJson('/api/posts')
        ->assertOk()
        ->assertJsonStructure([
            'data' => [['id', 'title', 'content', 'created_at']],
            'meta' => ['total', 'current_page', 'last_page'],
        ])
        ->assertJsonCount(15, 'data');
}
```

## Fluent JSON Assertions

For complex API responses, use `AssertableJson`:

```php
use Illuminate\Testing\Fluent\AssertableJson;

public function test_user_api_response_shape(): void
{
    $user = User::factory()->create();

    $this->actingAs($user)
        ->getJson('/api/profile')
        ->assertJson(fn (AssertableJson $json) =>
            $json->has('data', fn ($j) =>
                $j->where('id', $user->id)
                   ->where('email', $user->email)
                   ->whereType('created_at', 'string')
                   ->etc()
            )
        );
}
```

## Database Assertions

```php
public function test_creates_record_with_correct_attributes(): void
{
    $user = User::factory()->create();

    $this->actingAs($user)
        ->postJson('/api/posts', ['title' => 'Test', 'body' => 'Content']);

    $this->assertDatabaseHas('posts', [
        'title' => 'Test',
        'user_id' => $user->id,
    ]);
}

public function test_soft_deletes_record(): void
{
    $post = Post::factory()->create();

    $this->actingAs($post->user)
        ->deleteJson("/api/posts/{$post->id}");

    $this->assertSoftDeleted('posts', ['id' => $post->id]);
}
```

## N+1 Query Count Testing

```php
public function test_index_avoids_n_plus_one(): void
{
    Post::factory()->count(10)->create();

    $this->expectsDatabaseQueryCount(2); // 1 posts + 1 users (eager loaded)

    $this->getJson('/api/posts')->assertOk();
}
```

## Console / Artisan Command Testing

```php
public function test_inspire_command_succeeds(): void
{
    $this->artisan('inspire')->assertSuccessful();
}

public function test_command_output(): void
{
    $this->artisan('greet', ['name' => 'Taylor'])
        ->expectsOutput('Hello, Taylor!')
        ->assertSuccessful();
}

public function test_interactive_command(): void
{
    $this->artisan('make:user')
        ->expectsQuestion('What is the name?', 'John')
        ->expectsQuestion('What is the email?', 'john@example.com')
        ->expectsConfirmation('Are you sure?', 'yes')
        ->expectsOutput('User created!')
        ->assertSuccessful();
}

public function test_scheduled_command_runs_daily(): void
{
    $events = collect(app(Schedule::class)->events())
        ->filter(fn ($e) => str_contains($e->command, 'backup:run'));

    $this->assertCount(1, $events);
    $this->assertSame('0 0 * * *', $events->first()->expression);
}
```

## Debugging Helpers

```php
// Show full exception stack trace instead of HTTP error response
$this->withoutExceptionHandling()->get('/broken');

// Follow redirects automatically
$this->followingRedirects()->post('/login', $creds)->assertSee('Dashboard');

// Skip specific middleware for testing
$this->withoutMiddleware(ThrottleRequests::class)->get('/api/posts');
```
