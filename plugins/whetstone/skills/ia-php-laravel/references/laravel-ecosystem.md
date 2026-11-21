# Laravel Ecosystem Patterns

> When to read: when reaching for ecosystem features (notifications, queues, broadcasting, vector search, scheduling, file storage, mail) and needing the canonical Laravel approach.

## Notifications

Multi-channel dispatch (mail, SMS, Slack, database) from a single notification class.

```php
// Create: php artisan make:notification OrderShipped
class OrderShipped extends Notification implements ShouldQueue
{
    use Queueable;

    public function __construct(public readonly Order $order)
    {
    }

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
- Apply notification `middleware()` with a configured queue rate limiter for delivery frequency. `ShouldBeUnique` on a notification does not make Laravel's `SendQueuedNotifications` wrapper unique. For duplicate-event suppression, use a unique outer job or durable recipient/event deduplication; rate limiting alone does not provide that guarantee.
- **Enable `Illuminate\Mail\Markdown::withSecuredEncoding()` in `AppServiceProvider::boot()`** (available since v11.44.5); ordinary HTML escaping leaves Markdown links and images active in interpolated mail values, including `MailMessage::line()`. Through v13.35.0, even secured encoding permits backslash bypasses; v13.36.0 escapes backslashes and brackets. Secured encoding stays opt-in on every version. Keep user-controlled values out of Markdown link text and URL positions. Test rendered mail with a literal `\[x](https://example.invalid)` value and assert that it creates no link or image to that URL.

## Broadcasting

Server-side drivers in Laravel 13: Reverb (first-party WebSocket server, `php artisan install:broadcasting --reverb`), Pusher Channels, Ably, plus `log` for local debugging and `null` for tests. All three real-time drivers speak the Pusher channel protocol to Echo over a persistent WebSocket.

- **Mercure driver** (`MercureBroadcaster`, since v13.32.0; expect the published docs to lag). Transport is Server-Sent Events: the app publishes updates over HTTP to a Mercure hub (a standalone hub, or FrankenPHP's built-in one, which needs no `url`), and browsers subscribe with `EventSource`, so the application stack runs no WebSocket server process. Channel authorization is a JWT the hub validates (`secret`/`subscribe_secret` config; the hub multiplexes every joined channel over one connection under one token), `private-encrypted-*` channels are end-to-end encrypted with an `encryption_key` the hub never sees, and presence channels are never encrypted because member payloads go through the hub's subscription API. From v13.36.0, an event whose broadcast connections are all Mercure connections without `'async' => true` publishes synchronously inside the dispatching request, even when it implements `ShouldBroadcast`; a previously published `config/broadcasting.php` lacks the `async` key, so upgrading moves hub latency and failures (`BroadcastException`) from a retrying queue worker into the HTTP request. Set `'async' => (bool) env('MERCURE_ASYNC', false)` (the v13.36.0 config default) and enable it to queue again (it requires a `url`; the driver throws `InvalidArgumentException` without one), or implement `ShouldRescue` to keep publishing inline while containing hub errors. Also from v13.36.0, publishing through FrankenPHP's built-in hub (no `url`) from the CLI or a queue worker throws `BroadcastException`.
- **Audit `routes/channels.php` for integer casts when user keys are ULIDs or UUIDs.** The `install:broadcasting` stub before v13.43.0, and in every 12.x release through v12.73.0, generates `(int) $user->id === (int) $id`; every current ULID and `HasUuids` UUIDv7 key casts to `1`, so any user authorizes for every other user's private channel. Upgrading does not rewrite the published file. Compare with `(string) $user->id === (string) $id` (or `$user->is($model)` with model binding), and test that user A's request to authorize `private-App.Models.User.{B}` returns 403.

## Vector Search

- **Vector search** (Laravel 13, needs the Laravel AI SDK): `whereVectorSimilarTo('embedding', $queryEmbeddingOrText, minSimilarity: 0.4)` filters by cosine similarity (0.0-1.0) and orders most-similar first (`order: false` disables that); `selectVectorDistance(..., as: 'distance')`, `whereVectorDistanceLessThan()`, and `orderByVectorDistance()` expose raw distance. A string argument is embedded on the fly; pass a pre-computed array to skip the provider call. Supported on PostgreSQL with `pgvector` (`Schema::ensureVectorExtensionExists()`, `$table->vector('embedding', dimensions: 1536)->index()`), MariaDB 11.7+, and MongoDB via the Laravel MongoDB package; not MySQL or SQLite.

## Task Scheduling

Define recurring tasks in `routes/console.php`:

```php
use Illuminate\Support\Facades\Schedule;

// Artisan commands
Schedule::command('reports:generate')->dailyAt('02:00')->withoutOverlapping();
Schedule::command('cache:prune-stale-tags')->hourly();

// Closures for simple tasks
Schedule::call(fn () => DB::table('sessions')->where('last_active', '<', now()->subDay())->delete())
    ->daily()
    ->name('cleanup-sessions')
    ->withoutOverlapping();

// Queue jobs
Schedule::job(new ProcessDailyMetrics)->dailyAt('01:00');
```

Key methods:
- `->withoutOverlapping($minutes)`: cache-lock guard; the argument is the lock expiry (default 1440), not a timeout. A run killed without releasing the lock (SIGKILL, OOM) leaves the task skipped until expiry; clear it with `php artisan schedule:clear-cache` and size the expiry just above the longest run.
- `->onOneServer()`: every scheduler node must share one default cache store that supports atomic locks (`redis`, `memcached`, `database`, `dynamodb`); per-node `file`/`array` caches let every node run the task. Give closures distinct `->name()` values (required by `withoutOverlapping` too).
- `->evenInMaintenanceMode()`: critical tasks that must run during `php artisan down`
- `->runInBackground()`: don't block scheduler for long tasks
- `->emailOutputOnFailure('ops@example.com')`: alert on failures
- Requires system cron: `* * * * * cd /path && php artisan schedule:run >> /dev/null 2>&1`

`schedule:interrupt` signals cooperative shutdown; it does not preempt an event already executing. For a long command that must stop during deployment, process bounded batches, check cancellation between batches, and persist enough progress to resume. Use `Schedule::hasBeenInterruptedSince($startedAt)` only when the installed framework provides the timestamp-based interrupt implementation and interruption polling is enabled. Capture the command's start time once. Verify that a command started before the signal stops at its next checkpoint and one started after the signal continues; do not assume the scheduler's own loop interrupts command code.

## Custom Casts

Value objects for model attributes: encapsulate formatting, validation, and behavior.

```php
class Money implements CastsAttributes
{
    public function get(Model $model, string $key, mixed $value, array $attributes): MoneyValue
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
- `AsEncryptedCollection::class`: store encrypted collections in a `TEXT`-or-larger column. Encrypted contents cannot be searched or queried with JSON operators.
- `AsEnumCollection::class`: array of enums stored as JSON
- `AsStringable::class`: fluent string operations on attribute
- Enum casts: `'status' => OrderStatus::class` gives automatic PHP enum <-> DB value
- Encrypted cast: `'api_token' => 'encrypted'` gives transparent encrypt/decrypt for sensitive fields

Treat a nested model assignment such as `fill(['secrets->token' => $token])` separately from assigning the whole attribute. Before v13.35.0 (the encrypted-class JSON-path fix, framework PR #61834), `AsEncryptedArrayObject` and `AsEncryptedCollection` bypass their normal cast setter on this path. The old path can discard sibling values and save plaintext JSON. Until the installed `HasAttributes` implementation decrypts and re-encrypts encrypted class casts during JSON-path updates, read the cast value, modify it, reassign the whole attribute, and save the model. Verify raw persisted ciphertext and a fresh model's decrypted value, including preserved siblings. Query-builder JSON updates bypass this model path and need separate verification.

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

### Trusted proxies

Configure `->trustProxies(at: [...])` in `bootstrap/app.php` with the real proxy addresses; leaving it unset is not "trust nothing". From v11.45.2 in every later 11.x release (no 11.x fix), v12.22.0 through v12.72.0, and through v13.42.0, an unset proxy list trusts every caller when the client-supplied `Host` header ends in `.on-forge.com` or `.on-vapor.com`, so `X-Forwarded-For` sets `$request->ip()` and IP-keyed rate limits and allowlists can be bypassed. v13.43.0 and v12.73.0 (framework PR #62484) also require the Forge or Vapor environment variable. Test by sending `Host: x.on-forge.com` with `X-Forwarded-For: 10.9.9.9` and asserting `$request->ip()` is the socket address.

### Blade dynamic components

Affected through v13.42.0, and in 12.x through v12.72.0, `<x-dynamic-component component="..." :title="$value" />` passes a bound attribute that is not a constructor prop to `$attributes` unescaped, while the same binding on a static `<x-...>` tag is HTML-escaped; `ComponentAttributeBag` rewrites `"` to `\"`, which a browser does not treat as an escape. v13.43.0 (framework PR #62455) and v12.73.0 (framework PR #62456) fix it. On affected versions, use an echoed attribute (`title="{{ $value }}"`), which is escaped, or `e($value)` in the binding, for any user-influenced value. Test by rendering the dynamic tag with `'"><script>x</script>'` and asserting the output contains `&quot;&gt;`.

Through v13.42.0 and v12.72.0, `$attributes->merge()` leaves object defaults unescaped, so `merge(['title' => Str::of($input)])` or an `AsStringable` attribute renders raw HTML; v13.43.0 and v12.73.0 (framework PR #62503) escape every value that is not `Htmlable`. On affected versions, pass `(string)` or `e()` values to `merge()`. As hardening, choose the `component` name of `<x-dynamic-component>` from a server-side allowlist; from v13.43.0 and v12.73.0 (framework PRs #62453, #62454) names outside `[\w\-:.]` throw.

### Password Validation

```php
Password::min(12)->letters()->mixedCase()->numbers()->symbols()
```

### Signed URLs

`URL::temporarySignedRoute('download', now()->addMinutes(30), ['file' => $id])` with `signed` middleware for tamper-proof temporary access. Pass signed-route parameters by name. Before v13.41.0 and v12.72.0 (framework PR #62401), positional parameters beyond the route's placeholders are appended unencoded, so a user-influenced value of `expires=` blanks the expiry and yields a never-expiring signed URL.

### File Uploads

- Validate MIME type: `'file' => ['required', 'mimes:pdf,docx', 'max:10240']`
- Store outside public disk: `$request->file('doc')->store('documents', 's3')`
- Store the validated value, not a fresh read: in a form request, `$request->validated('doc')?->store('documents', 's3')`; with inline validation, `$request->validate([...])['doc']->store('documents', 's3')`. From v13.25.0 through v13.42.0 (fixed in v13.43.0, framework PR #62521), an empty text field with the same name hides the file from validation, so an optional rule such as `nullable|mimes:pdf` passes while `$request->file('doc')` returns the unvalidated upload. Test by posting both `doc=` and a `.php` file under `doc` and asserting a 422.
- Never trust the original filename

### Dependency Audit

`composer audit` checks for known CVEs in dependencies. Run in CI.

### Logging PII

Never log raw user data. Use `[REDACTED]` pattern for sensitive fields in log context.
