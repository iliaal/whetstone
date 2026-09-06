# Factory Patterns

> When to read: when writing or refactoring Laravel model factories — basic shapes, states, sequences, relationships, and seed-vs-test boundaries.

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

Name states as adjectives or past participles -- they describe what the model IS:

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

`Factory::makeInstance()` wraps `new $model($attributes)` in `Model::unguarded(...)`, so a factory can set a column that `$fillable` would reject and `$guarded` would block. This is convenient for seeding and dangerous for evidence: a test whose fixture stamps a non-fillable column pins a row shape the runtime **cannot** produce, so the guard, resource, or query it asserts on is being exercised against data no production writer can create.

Mechanical check for any test that pins a guard, a filter, or a "this column decides X" behaviour: diff the factory payload's keys against the model's `$fillable`. A key present in the payload and absent from `$fillable` means the fixture is unreachable, and the assertion proves nothing about production. The tell in a suite is a sibling test setting the same column to `null` while the guard test stamps a real value -- both shapes exist, only one of them can happen.

The neighbouring question is the same one in the other direction: for every precondition the fixture supplies, name the production actor that supplies it. "Nothing does" is the finding.
