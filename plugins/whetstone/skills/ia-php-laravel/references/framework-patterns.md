# Framework and boundary patterns

## Modern PHP (8.4)

Use when applicable -- no explanatory comments for these in generated code:
- Readonly classes/properties for immutable data; constructor promotion with readonly
- Enums with methods and interfaces for domain constants
- Match expressions over switch
- First-class callable syntax `$fn = $obj->method(...)`
- Fibers for cooperative async when Swoole/ReactPHP not available
- DNF types `(Stringable&Countable)|null` for complex constraints
- Property hooks: `public string $name { get => strtoupper($this->name); set => trim($value); }`
- Asymmetric visibility: `public private(set) string $name` -- public read, private write
- `new` without parentheses in chains: `new MyService()->handle()`
- `array_find()`, `array_any()`, `array_all()` -- native array search/check without closures wrapping Collection


## Laravel Architecture

- **Escalate structure only when it pays for itself.** Simple CRUD → a fat Eloquent model + Form Request is correct; do not add layers. Reach for an **Action class** when an operation crosses model boundaries or gains a 3rd caller. Extract a **non-Eloquent domain object** only when a business rule needs testing without booting the DB, or protects an invariant the model can't. Default down the ladder, not up -- an unused abstraction is a defect, not foresight.
- **Thin controllers** -- only validate, call service/action, return response. Domain behavior (scopes, accessors, relationships) lives in models; cross-cutting orchestration in service classes.
- **Never call `env()` outside `config/`.** Wherever `php artisan config:cache` has run (the deploy sequence requires it, so typically production), every `env()` call outside a config file returns `null` -- silently, with no error. Read through `config('services.github.token')` and put third-party credentials in `config/services.php` rather than inventing a new config file.
- **A closure inside a `config/*.php` file breaks `config:cache`.** The cache file is written with `var_export`, which cannot represent a closure, so a hook registered as `fn ($event) => ...` works locally and aborts the deploy step with `Your configuration files are not serializable`. Register callables as `[SomeClass::class, 'method']` arrays. This is the opposite of `route:cache`, which serializes closure actions rather than rejecting them (Routing, below).
- **Service classes** for business logic with readonly DI: `__construct(private readonly PaymentService $payments)`
- **`#[Scoped]` resets in exactly one place in the framework: the queue worker, between jobs** -- never at a transaction boundary, so a memo filled inside `DB::transaction()` survives the rollback for the rest of the request or job. Full mechanism in [common-pitfalls.md](./common-pitfalls.md).
- **Action classes** (single-purpose invokable) for operations crossing service boundaries
- **Form Requests** for all validation -- never inline in controllers, never inside services. Add `toDto()` so services receive typed, pre-validated data; internal code trusts that input was validated at the boundary.
- **An ownership check in the controller body runs AFTER validation, so a foreign-but-existing id plus an invalid payload returns 422 while a non-existent id returns 404 -- an existence oracle.** Move it into `FormRequest::authorize()` with `failedAuthorization()` throwing `NotFoundHttpException`; the natural "other tenant gets 404" test posts a valid payload and cannot see it. Full mechanism in [common-pitfalls.md](./common-pitfalls.md).
- Conditional validation: `Rule::requiredIf()`, `sometimes`, `exclude_if`
- **`'field' => ['array:a,b']` restricts which keys may appear; it requires none of them** -- but OpenAPI generators publish that key list as the object's `required` array, so never read a generated `required` list as the endpoint's contract. Full mechanism in [common-pitfalls.md](./common-pitfalls.md).
- **Events + Listeners** for side effects (notifications, logging, cache invalidation) -- not in services. Name events past-tense in business terms (`OrderPlaced`, not `OrderRecordUpdated`). Carry IDs and changed facts in the payload, **not the full Eloquent model** -- `SerializesModels` re-fetches by key when a queued listener runs, so a model passed in-memory goes stale (same desync class as the observer/stale-copy pitfall below).
- Feature folder organization over type-based past ~20 models


## Routing

- Scoped route model binding to prevent cross-tenant access: `Route::scopeBindings()->group(fn() => ...)`
- `Route::model('conversation', AiConversation::class)` for custom binding resolution
- API resource routes: `Route::apiResource('posts', PostController::class)` -- index/store/show/update/destroy without create/edit
- **Laravel 12 `route:cache` serializes closure actions instead of throwing `LogicException: Uses Closure`**, so a closure capturing `$this` from a service provider drags the bound container into the cached payload. It balloons but still terminates; unbounded blowup needs a real reference cycle. Fix: an invokable controller, or `use ($var)` instead of `$this`. Full mechanism in [common-pitfalls.md](./common-pitfalls.md).


## API Resources

- `whenLoaded()` for relationships -- prevents N+1 in responses
- `when()` / `mergeWhen()` for permission-based fields; `whenPivotLoaded()` for pivot data
- `withResponse()` for custom headers, `with()` for metadata (version, pagination)
- **`parent::toArray($request)` calls the parent RESOURCE's `toArray()`, not the framework's attribute spread.** It spreads every model attribute only when the class extends `JsonResource` directly; through an ancestor resource returning an explicit array literal the column is never serialised, `$hidden` or not. Resolve the `extends` chain before claiming either. Full mechanism in [common-pitfalls.md](./common-pitfalls.md).
- **A nested `JsonResource` wrapping `null` serialises to JSON `null`, and the child's `toArray()` never runs** -- `filter()` replaces the value before `resolve()` reaches the child, so `Resource::make($nullable)` and an explicit ternary are byte-identical on the wire. Probe through the parent's `resolve($request)`, never `json_encode()`. Full mechanism in [common-pitfalls.md](./common-pitfalls.md).


## API Design

- **Contract-first**: define the API Resource (response contract) and Form Request (input contract) before writing the controller.
- Never return raw models or `toArray()` from controllers -- Resources control exactly what's serialized. Every observable field, ordering, or timing becomes a caller dependency (Hyrum's Law).
- **Add, don't modify**: new fields/endpoints over changing or removing existing ones. Deprecate first (`@deprecated` in OpenAPI/docblock), remove in a later version.
- **Consistent envelope**: `{ "success": bool, "data": ..., "error": null, "meta": {} }`. Normalize `ValidationException`, `ModelNotFoundException`, `AuthorizationException`, and application errors to `{ "success": false, "error": { "code": "...", "message": "..." } }` in the exception handler -- callers build error handling once.
- **Isolate third-party SDKs behind an adapter class.** Catch vendor exceptions (`GuzzleHttp\Exception\ClientException`, `Stripe\Exception\*`) inside the adapter and rethrow as domain exceptions (`PaymentFailedException`) -- never let a Guzzle/Stripe exception bubble into a controller or service.
- **Never return the raw vendor object** (`Stripe\Charge`, a Guzzle `Response`) from an adapter -- map it to a DTO first. Otherwise every vendor field becomes a caller dependency (Hyrum's Law), same as returning raw models on egress.
- **Third-party responses are untrusted data**: validate shape and content through the DTO before use in logic or rendering. Inject the specific client/credentials the adapter needs, not the whole config or container.
- **`Http::timeout($n)` is per redirect hop, not per logical call** -- Guzzle re-invokes the handler per hop with the same options, so the ceiling is `(max_redirects + 1) x timeout`: 90s at `timeout(15)`. Anything sized off that aggregate inherits the error (lock expiries, queue `$timeout`, SLOs). Full mechanism in [common-pitfalls.md](./common-pitfalls.md).
