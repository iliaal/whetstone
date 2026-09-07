---
name: ia-php-laravel
class: language
description: >-
  Modern PHP 8.4 and Laravel patterns: architecture, Eloquent, migrations, queues, testing.
  Use when working with Laravel, Eloquent, Blade, artisan, or building/testing a
  framework-based PHP app. Not for php-src internals, standalone PHP libraries, or
  general PHP language discussion.
paths: "**/*.php"
---

# PHP & Laravel Development

Scoped to framework-level PHP. Work on php-src internals or a native PHP extension is C, not PHP: the `ia-c-systems` skill covers it, including the Zend API conventions (`gen_stub` arginfo, the request-scoped allocator, custom object handlers, `.phpt`).

## Working rules

- Keep simple CRUD simple; extract cross-model orchestration only when it has a concrete use.
- Validate and authorize at request boundaries; serialize through explicit resources and validate third-party responses.
- Preserve deployed migration history, queued payload compatibility, and concurrent writes.
- Verify cache compilation, queue execution, and HTTP behavior through their real entrypoints when those paths change.

## Code Style

- `declare(strict_types=1)` in every file
- Happy path last -- guards and errors first, success at the end. Early returns, no `else`.
- Comments explain *why*, never *what*. Never comment tests. If code needs a "what" comment, rename or restructure.
- No single-letter variables -- `$exception` not `$e`, `$request` not `$r`
- `?string` not `string|null`. Always specify `void`. Import classnames, never inline FQN.
- **Widening one parameter to `?T` obliges auditing every call site that forwards the same value** -- the sibling call still declares `string`, and `null` throws a `TypeError` there even with no `declare(strict_types=1)`, because coercive mode never coerces `null` into a scalar. Strictness is decided by the file the CALL is written in, never by the callee's file. Full mechanism in [common-pitfalls.md](./references/common-pitfalls.md).
- Validation uses array notation `['required', 'email']` for easier custom rule classes
- PHPStan level 8+ (`phpstan analyse --level=8`); aim for 9 on new projects. `@phpstan-type` / `@phpstan-param` for generic collection types. The missing-iterable-value-type check lands at **level 6** (and every level above it), so any project at 8+ inherits it: use the generic form on every iterable -- `@return Collection<int, User>`, `@param array<int, MyObject>` -- and array-shape notation `array{first: SomeClass, second: SomeClass}` for fixed-key returns; a bare `Collection` or `array` will not clear it.


## Discipline

- Simplicity first -- every change as simple as possible, minimal code impact
- Only touch what's necessary -- no unrelated changes
- No hacky workarounds -- if a fix feels wrong, step back and implement the clean solution
- New abstraction requires 3+ usage sites; otherwise inline it
- No empty catch blocks -- log or rethrow, never swallow
- Verify before declaring done: `./vendor/bin/phpstan analyse --level=8 && ./vendor/bin/phpunit` with zero warnings
- Checkpoint per stage, not only at the end: `migrate:status` after a migration, `route:list --path=<prefix>` after routing changes, `queue:work --once` after adding a job, `pint --test` before the PR -- each catches its failure class while the change is small


## References

- [laravel-ecosystem.md](./references/laravel-ecosystem.md) -- Notifications, Task Scheduling, Custom Casts
- [testing.md](./references/testing.md) -- PHPUnit essentials, data providers, running tests
- [feature-testing.md](./references/feature-testing.md) -- Auth, validation, API, console, DB assertions
- [mocking-and-faking.md](./references/mocking-and-faking.md) -- Facade fakes, action mocking, Mockery
- [factories.md](./references/factories.md) -- States, relationships, sequences, afterCreating hooks
- [production-performance.md](./references/production-performance.md) -- OPcache, JIT, preloading, deploy caches
- [common-pitfalls.md](./references/common-pitfalls.md) -- event-layer bypasses, FK cascades, pivot writes, resource and request-shape traps
- [pitfalls-deep.md](./references/pitfalls-deep.md) -- afterCommit alternatives, observer desync, jsonb race, savepoints, validation-rule internals

## Task-specific references

Read the relevant reference before implementing or reviewing the matching behavior:

- For PHP features, controller/action design, routing, resources, or external APIs: [framework-patterns.md](./references/framework-patterns.md).
- For migrations, Eloquent writes, casts, queues, job payloads, or production startup: [persistence-and-jobs.md](./references/persistence-and-jobs.md).
- For PHPUnit work or changes affecting events, serialization, validation, or lifecycle behavior: [testing-and-pitfalls.md](./references/testing-and-pitfalls.md).

Existing specialized references, when the corresponding topic applies:
