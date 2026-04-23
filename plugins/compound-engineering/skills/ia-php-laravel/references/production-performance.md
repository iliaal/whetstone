# Production Performance — OPcache, JIT, Preloading, Laravel caches

Load this reference when deploying a PHP/Laravel application to production or optimizing runtime performance. Not relevant for dev or testing.

- **OPcache**: enable in production (`opcache.enable=1`), set `opcache.memory_consumption=256`, `opcache.max_accelerated_files=20000`. Validate with `opcache_get_status()`.
- **JIT**: enable with `opcache.jit_buffer_size=100M`, `opcache.jit=1255` (tracing). Biggest gains on CPU-bound code (math, loops), minimal impact on I/O-bound Laravel requests.
- **Preloading**: `opcache.preload=preload.php` — preload framework classes and hot app classes. Use `composer dumpautoload --classmap-authoritative` in production.
- **Laravel-specific**: `php artisan config:cache && php artisan route:cache && php artisan view:cache && php artisan event:cache` — run on every deploy. `composer install --optimize-autoloader --no-dev` for production.
