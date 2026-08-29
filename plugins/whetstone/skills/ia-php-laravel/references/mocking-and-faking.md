# Mocking and Faking

Fake facades BEFORE the action that triggers them. Assert AFTER.

## Queue Faking

```php
public function test_dispatches_job_on_post_creation(): void
{
    Queue::fake();

    $user = User::factory()->create();
    $this->actingAs($user)
        ->postJson('/api/posts', ['title' => 'Test', 'body' => 'Content']);

    Queue::assertPushed(ProcessPost::class, fn ($job) => $job->post->title === 'Test');
    Queue::assertPushed(ProcessPost::class, 1); // exact count
}
```

## Event Faking

```php
public function test_fires_event_on_publish(): void
{
    Event::fake([PostPublished::class]);

    $post = Post::factory()->create();
    $post->publish();

    Event::assertDispatched(PostPublished::class, fn ($e) => $e->post->id === $post->id);
}
```

## Notification Faking

```php
public function test_sends_notification_to_post_author(): void
{
    Notification::fake();

    $post = Post::factory()->create();
    $post->approve();

    Notification::assertSentTo($post->user, PostApproved::class);
}
```

## Mail Faking

```php
public function test_sends_welcome_email(): void
{
    Mail::fake();

    $this->postJson('/api/register', [
        'email' => 'new@example.com',
        'password' => 'secret123',
    ]);

    Mail::assertSent(WelcomeMail::class, fn ($mail) => $mail->hasTo('new@example.com'));
}
```

## Storage Faking

```php
public function test_uploads_avatar(): void
{
    Storage::fake('public');
    $user = User::factory()->create();
    $file = UploadedFile::fake()->image('avatar.jpg');

    $this->actingAs($user)
        ->postJson('/api/avatar', ['avatar' => $file])
        ->assertOk();

    Storage::disk('public')->assertExists("avatars/{$file->hashName()}");
}
```

## HTTP Faking (External APIs)

```php
public function test_fetches_data_from_external_api(): void
{
    Http::fake([
        'api.example.com/*' => Http::response(['data' => ['id' => 1, 'name' => 'Test']], 200),
    ]);

    $service = app(ExternalApiService::class);
    $result = $service->fetchData();

    $this->assertSame('Test', $result['name']);

    Http::assertSent(fn ($request) =>
        $request->url() === 'https://api.example.com/data'
        && $request->hasHeader('Authorization')
    );
}
```

Use `Http::preventStrayRequests()` after faking to fail on any unfaked URL -- catches accidental real HTTP calls:

```php
Http::fake(['api.example.com/*' => Http::response(['ok' => true])]);
Http::preventStrayRequests(); // any other URL throws an exception
```

## Bus Faking (Batches & Chains)

```php
public function test_dispatches_batch(): void
{
    Bus::fake();

    $this->postJson('/api/import', ['file' => $file]);

    Bus::assertBatched(fn ($batch) => $batch->jobs->count() === 10);
}

public function test_dispatches_chain(): void
{
    Bus::fake();

    $this->postJson('/api/process');

    Bus::assertChained([ValidateJob::class, ProcessJob::class, NotifyJob::class]);
}
```

## Action Testing with resolve() + swap()

For invokable action classes, resolve from the container so DI works. Use `swap()` to replace dependencies with mocks:

```php
public function test_processes_order_and_notifies(): void
{
    $user = User::factory()->create();
    $order = Order::factory()->for($user)->create();

    // Mock dependency action and swap into container
    $calculateTotal = Mockery::mock(CalculateOrderTotalAction::class);
    $calculateTotal->shouldReceive('__invoke')
        ->once()
        ->with($order)
        ->andReturn(10000);
    $this->swap(CalculateOrderTotalAction::class, $calculateTotal);

    $notifyAction = Mockery::mock(NotifyOrderCreatedAction::class);
    $notifyAction->shouldReceive('__invoke')->once()->with($order);
    $this->swap(NotifyOrderCreatedAction::class, $notifyAction);

    // resolve() pulls from container with mocked dependencies injected
    $result = resolve(ProcessOrderAction::class)($order);

    $this->assertSame(10000, $result->total);
}
```

Only mock what you own -- for external services (Stripe, etc.), create a service abstraction with a driver pattern and swap the driver config in tests, instead of mocking the SDK directly.

## Mockery (Service Mocking)

For non-facade services where DI mocking is needed:

```php
public function test_sends_notification_to_active_users(): void
{
    $repository = Mockery::mock(UserRepository::class);
    $repository->shouldReceive('findActive')
        ->once()
        ->andReturn(User::factory()->count(2)->make());

    $this->app->instance(UserRepository::class, $repository);

    $service = app(NotificationService::class);
    $result = $service->notifyActiveUsers('Important message');

    $this->assertSame(2, $result->count());
}
```

Prefer Laravel facade fakes over Mockery when both options exist. Use Mockery for custom services and repository interfaces.

## Time Travel

For testing time-dependent logic (expiration, scheduling, "created N days ago"):

```php
public function test_marks_overdue_orders(): void
{
    $order = Order::factory()->create();

    $this->travel(31)->days();

    $this->artisan('orders:mark-overdue')->assertSuccessful();

    $this->assertDatabaseHas('orders', [
        'id' => $order->id,
        'status' => 'overdue',
    ]);

    $this->travelBack(); // reset to real time
}

public function test_timestamps_match_frozen_time(): void
{
    $this->freezeTime();

    $user = User::factory()->create();

    $this->assertSame(now()->toDateTimeString(), $user->created_at->toDateTimeString());
}

public function test_subscription_expires(): void
{
    $user = User::factory()->create();
    $subscription = Subscription::factory()->create([
        'user_id' => $user->id,
        'expires_at' => now()->addDays(30),
    ]);

    $this->travelTo(now()->addDays(31));

    $this->assertTrue($subscription->fresh()->isExpired());
}
```

Available time units: `seconds()`, `minutes()`, `hours()`, `days()`, `weeks()`, `months()`, `years()`. Always call `$this->travelBack()` or use `$this->freezeTime()` to avoid leaking time state between tests.

## Http::assertSent() passes on ANY match

`Http::assertSent()` passes when ANY recorded request satisfies the callback -- not every request, and not necessarily the one under test. The common shape, an early `return true` for requests the test does not care about, makes every unrelated request satisfy the whole assertion on its own, so the clause that matters never has to hold. Return `false` for out-of-scope requests, then assert on the single request under test; `assertNotSent` inverts the same way. Prove the assertion is live by mutating the source to violate what it claims to guard and re-running that test alone -- a still-green run means the assertion was never doing anything. Related: after making a straying test hermetic, ask what the live response was doing for the suite; a stray call can be load-bearing coverage, and removing it is a coverage regression disguised as a hygiene fix.

## Mail::fake() does not render the view

`Mail::fake()` records mailables without building them, so `assertSent`/`assertQueued` never compiles the Blade view. A renamed view variable, a dropped `Content::with()` key, or a `Storage::disk()->url()` on an unconfigured disk all pass CI and throw on the first real send. Force a render: assert on `(new TheMailable(...))->render()`, or call `$mail->assertSeeInHtml(...)` inside the assertion closure, which renders as a side effect. When a mailable or its template changes, confirm at least one test forces a render -- "there is a test for this email" is not "the template compiles".

## Mail::fake() vs Notification::fake(): different dispatch surfaces

`Mail::fake()` swaps the transport; `Notification::fake()` swaps the whole dispatcher. Under `Mail::fake()` the notification pipeline still runs -- channels resolve, `send()` executes, and `NotificationSending` / `NotificationSent` fire, so listeners on those events run. Under `Notification::fake()` nothing dispatches and neither event fires. Switching a test from one to the other to use `assertSentTo()` silently stops every `NotificationSent` listener, so an assertion on that listener's side effect either fails or passes vacuously. When a diff moves a side effect onto such a listener, audit every test asserting it: assert what the caller itself sets under the fake, and cover the listener separately by constructing `new NotificationSent(...)` and calling `handle()`.

## throttle middleware and cache.limiter

`throttle` middleware reads `config('cache.limiter')`, not `cache.default`, so `Cache::flush()` does not reset rate-limit counters. With `cache.limiter` hardcoded to a real store, counters go to Redis even when `phpunit.xml` sets `CACHE_STORE=array`, and they accumulate across methods, runs and processes keyed by a constant IP or token -- a later test 429s before reaching its own limit, so the file passes alone and flakes in the suite with "expected 422, received 429". Clear the limiter's own store in `setUp()`: `Cache::store(is_string($s = config('cache.limiter')) ? $s : null)->clear()`. Use `clear()`, not `flush()` (not declared on the `Repository` contract, so PHPStan rejects it), and read the loop bound from the same config the limiter uses instead of a hardcoded literal.
