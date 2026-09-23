# Laravel Ecosystem Patterns

> When to read: when reaching for ecosystem features (notifications, queues, broadcasting, vector search, scheduling, file storage, mail) and needing the canonical Laravel approach.

## Notifications

Multi-channel dispatch (mail, SMS, Slack, database) from a single notification class.

```php
// Create: php artisan make:notification OrderShipped
class OrderShipped extends Notification implements ShouldQueue
{
    use Queueable;

    public function via(object $notifiable): array
    {
        // Channel selection per user preference
        return $notifiable->prefers_sms
            ? ['vonage']
            : ['mail', 'database'];
    }

    public function toMail(object $notifiable): MailMessage
    {
        return (new MailMessage)
            ->subject('Order Shipped')
            ->line("Order #{$this->order->id} has shipped.")
            ->action('Track Order', url("/orders/{$this->order->id}"));
    }

    public function toArray(object $notifiable): array
    {
        // Stored in `notifications` table for in-app display
        return ['order_id' => $this->order->id, 'status' => 'shipped'];
    }
}

// Dispatch
$user->notify(new OrderShipped($order));

// Bulk (uses queue automatically)
Notification::send($users, new OrderShipped($order));
```

- Always implement `ShouldQueue`; notifications are side effects, never block the request
- Use `toArray()` for database channel; it powers in-app notification feeds
- Read: `$user->unreadNotifications`, mark: `$notification->markAsRead()`
- Rate limit with `ShouldBeUnique` to prevent notification spam

## Broadcasting

Server-side drivers in Laravel 13: Reverb (first-party WebSocket server, `php artisan install:broadcasting --reverb`), Pusher Channels, Ably, plus `log` for local debugging and `null` for tests. All three real-time drivers speak the Pusher channel protocol to Echo over a persistent WebSocket.

- **Mercure driver** (`MercureBroadcaster`, merged into the 13.x branch after 13.31.0; confirm the installed release ships `Illuminate\Broadcasting\Broadcasters\MercureBroadcaster` before depending on it, and expect the published docs to lag). Transport is Server-Sent Events: the app publishes updates over HTTP to a Mercure hub (a standalone hub, or FrankenPHP's built-in one, which needs no `url`), and browsers subscribe with `EventSource`, so the application stack runs no WebSocket server process. Channel authorization is a JWT the hub validates (`secret`/`subscribe_secret` config; the hub multiplexes every joined channel over one connection under one token), `private-encrypted-*` channels are end-to-end encrypted with an `encryption_key` the hub never sees, and presence channels are never encrypted because member payloads go through the hub's subscription API.

## Vector Search

- **Vector search** (Laravel 13, needs the Laravel AI SDK): `whereVectorSimilarTo('embedding', $queryEmbeddingOrText, minSimilarity: 0.4)` filters by cosine similarity (0.0-1.0) and orders most-similar first (`order: false` disables that); `selectVectorDistance(..., as: 'distance')`, `whereVectorDistanceLessThan()`, and `orderByVectorDistance()` expose raw distance. A string argument is embedded on the fly; pass a pre-computed array to skip the provider call. Supported on PostgreSQL with `pgvector` (`Schema::ensureVectorExtensionExists()`, `$table->vector('embedding', dimensions: 1536)->index()`), MariaDB 11.7+, and MongoDB via the Laravel MongoDB package; not MySQL or SQLite.

## Task Scheduling

Define recurring tasks in `routes/console.php`:

```php
// Artisan commands
$schedule->command('reports:generate')->dailyAt('02:00')->withoutOverlapping();
$schedule->command('cache:prune-stale-tags')->hourly();

// Closures for simple tasks
$schedule->call(fn () => DB::table('sessions')->where('last_active', '<', now()->subDay())->delete())
    ->daily()
    ->name('cleanup-sessions')
    ->withoutOverlapping();

// Queue jobs
$schedule->job(new ProcessDailyMetrics)->dailyAt('01:00');
```

Key methods:
- `->withoutOverlapping()`: prevent concurrent runs (uses cache lock)
- `->onOneServer()`: run only on one server in multi-server setup
- `->evenInMaintenanceMode()`: critical tasks that must run during `php artisan down`
- `->runInBackground()`: don't block scheduler for long tasks
- `->emailOutputOnFailure('ops@example.com')`: alert on failures
- Requires system cron: `* * * * * cd /path && php artisan schedule:run >> /dev/null 2>&1`

## Custom Casts

Value objects for model attributes: encapsulate formatting, validation, and behavior.

```php
class Money implements CastsAttributes
{
    public function get(Model $model, string $key, mixed $value, array $attributes): Money
    {
        return new MoneyValue(
            amount: (int) $value,
            currency: $attributes['currency'] ?? 'USD'
        );
    }

    public function set(Model $model, string $key, mixed $value, array $attributes): array
    {
        return ['price' => $value->amount, 'currency' => $value->currency];
    }
}

// Usage on model
protected function casts(): array
{
    return ['price' => Money::class];
}
```

Built-in casts to prefer over manual accessors:
- `AsEncryptedCollection::class`: encrypt JSON columns at rest
- `AsEnumCollection::class`: array of enums stored as JSON
- `AsStringable::class`: fluent string operations on attribute
- Enum casts: `'status' => OrderStatus::class` gives automatic PHP enum <-> DB value
- Encrypted cast: `'api_token' => 'encrypted'` gives transparent encrypt/decrypt for sensitive fields

## Security Hardening

### Session

- `SESSION_HTTP_ONLY=true`, `SESSION_SAME_SITE=strict` in `.env`
- Regenerate session on login: `$request->session()->regenerate()` in auth controller
- `SESSION_LIFETIME`: set appropriate timeout (120 min default is often too long)

### Security Headers Middleware

```php
class SecurityHeaders
{
    public function handle($request, Closure $next)
    {
        $response = $next($request);
        $response->headers->set('X-Frame-Options', 'DENY');
        $response->headers->set('X-Content-Type-Options', 'nosniff');
        $response->headers->set('Referrer-Policy', 'strict-origin-when-cross-origin');
        $response->headers->set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');
        $response->headers->set('Content-Security-Policy', "default-src 'self'");
        return $response;
    }
}
```

Register in `bootstrap/app.php` middleware stack.

### Password Validation

```php
Password::min(12)->letters()->mixedCase()->numbers()->symbols()
```

### Signed URLs

`URL::temporarySignedRoute('download', now()->addMinutes(30), ['file' => $id])` with `signed` middleware for tamper-proof temporary access.

### File Uploads

- Validate MIME type: `'file' => ['required', 'mimes:pdf,docx', 'max:10240']`
- Store outside public disk: `$request->file('doc')->store('documents', 's3')`
- Never trust the original filename

### Dependency Audit

`composer audit` checks for known CVEs in dependencies. Run in CI.

### Logging PII

Never log raw user data. Use `[REDACTED]` pattern for sensitive fields in log context.
