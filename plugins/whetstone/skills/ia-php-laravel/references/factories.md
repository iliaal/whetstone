# Factory Patterns

> When to read: when writing or refactoring Laravel model factories: basic shapes, states, sequences, relationships, and seed-vs-test boundaries.

## Basic Factory

```php
class PostFactory extends Factory
{
    public function definition(): array
    {
        return [
            'title' => fake()->sentence(),
            'slug' => fake()->slug(),
            'content' => fake()->paragraphs(3, true),
            'published_at' => fake()->dateTimeBetween('-1 year', 'now'),
            'user_id' => User::factory(),
            'category_id' => Category::factory(),
        ];
    }
}
```

## States

Name states as adjectives or past participles; they describe what the model IS:

```php
public function unpublished(): static
{
    return $this->state(fn (array $attributes) => [
        'published_at' => null,
    ]);
}

public function published(): static
{
    return $this->state(fn (array $attributes) => [
        'published_at' => now(),
    ]);
}

// Usage
$post = Post::factory()->unpublished()->create();
```

## Relationships

```php
// Has many -- creates parent with 3 children
$post = Post::factory()
    ->has(Comment::factory()->count(3))
    ->create();

// Belongs to -- creates children for specific parent
$posts = Post::factory()
    ->count(3)
    ->for($user)
    ->create();

// Combined
$post = Post::factory()
    ->published()
    ->for($user)
    ->has(Comment::factory()->count(3))
    ->has(Tag::factory()->count(2))
    ->create();
```

## afterCreating Hooks

For side effects that require a persisted model:

```php
public function configure(): static
{
    return $this->afterCreating(function (Post $post) {
        $post->tags()->attach(
            Tag::factory()->count(3)->create()
        );
    });
}
```

## Sequences

```php
$users = User::factory()
    ->count(3)
    ->sequence(
        ['role' => 'admin'],
        ['role' => 'editor'],
        ['role' => 'viewer'],
    )
    ->create();
```

## Usage in Tests

```php
// Single model
$user = User::factory()->create();

// With overrides
$user = User::factory()->create(['email' => 'specific@test.com']);

// Multiple
$posts = Post::factory()->count(10)->create();

// In-memory (no DB write)
$user = User::factory()->make();
```

Always use `create()` for feature tests (persists to DB). Use `make()` only for unit tests that need a model instance without persistence.

## Factories build the model unguarded

`Factory::makeInstance()` wraps `new $model($attributes)` in `Model::unguarded(...)`, so a factory can set a column that `$fillable` would reject and `$guarded` would block. A non-fillable fixture attribute therefore needs a production-writer check; it is not proof of an unreachable row. `$fillable` governs mass assignment, while direct property assignment followed by `save()`, query-builder writes, observers, or database defaults can supply the same value.

For any test that pins a guard, a filter, or a "this column decides X" behaviour, compare the factory payload with the model's mass-assignment rules, then trace the actual production writers for mismatches. Compare sibling fixtures using `null` and real values against those write paths. Reject a fixture as unreachable only after establishing that no relevant production path can produce its preconditions; do not discard an assertion solely because an attribute is absent from `$fillable`.

The neighbouring question is the same one in the other direction: for every precondition the fixture supplies, name the production actor that supplies it. "Nothing does" is the finding.
