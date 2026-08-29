# PHP extension C

The dialect rules for C written against the Zend Engine. These **override** the corresponding SKILL.md sections. Load before applying the layout, macro, or error-model rules to any file containing `PHP_FUNCTION`, `zend_`, `php_*.h`, or a `config.m4`.

## How the base rules resolve here

Most base rules already defer to project convention; this is what that convention turns out to be. Only formatting and the type choice override outright.

| Base rule | How it resolves in an extension |
|---|---|
| Repo formatting (`.clang-format`) | **Tabs.** php-src `CODING_STANDARDS.md` mandates them; extensions follow, regardless of any local preference. |
| No macro containing `return`, unless the project sanctions one | The project sanctions several. `RETURN_*`, `RETURN_THROWS()`, and `ZEND_PARSE_PARAMETERS_END()` return; they are mandatory idiom, not violations. `RETVAL_*` is the one that does **not** return: it assigns `return_value` and deliberately continues, which is the whole reason both spellings exist. |
| `goto` only where the repo sanctions it | The repo sanctions it. `goto cleanup` is the standard multi-resource release idiom throughout php-src. |
| Adopt the project's status type, else one enum per module | `zend_result` (`SUCCESS`/`FAILURE`) already exists. Do not invent a parallel enum beside it. |
| Exact-width types only where the representation is externally fixed | Here the project types win outright: `zend_long`, `zend_ulong`, `size_t`, `zend_string *`. `zend_long` is 32 or 64 bit by build, so never assume `int64_t`. |

## Build and test loop

```bash
phpize && ./configure --enable-<ext> && make -j$(nproc)
make test                                    # runs .phpt files under tests/
TESTS=tests/foo.phpt make test               # single test
php -d extension=modules/<ext>.so -r '...'   # ad-hoc probe
```

Tests are `.phpt`: `--TEST--`, optional `--SKIPIF--`, `--FILE--`, then `--EXPECT--` or `--EXPECTF--`. Prefer `--EXPECTF--` with `%d`/`%s` wherever output carries addresses, paths, or floats.

## Arginfo is generated, never hand-written

Signatures live in `<ext>.stub.php`. Regenerate with php-src's `build/gen_stub.php`, which writes `<ext>_arginfo.h`.

Editing `*_arginfo.h` by hand is always a bug: the next regeneration silently discards it, and the stub and the header disagree in the meantime. Change the stub, regenerate, commit both.

## Argument parsing

`ZEND_PARSE_PARAMETERS_START` must run **before any allocation or resource acquisition** in the function. It returns on failure, so anything acquired above it leaks on the error path.

```c
PHP_FUNCTION(ext_encode)
{
	zend_string *input = NULL;
	zend_long flags = 0;

	ZEND_PARSE_PARAMETERS_START(1, 2)
		Z_PARAM_STR(input)
		Z_PARAM_OPTIONAL
		Z_PARAM_LONG(flags)
	ZEND_PARSE_PARAMETERS_END();

	/* allocations start only after this line */
}
```

`Z_PARAM_OBJ_OF_CLASS` yields a `zend_object *`, not a `zval *`. Dereference user-supplied array elements with `ZVAL_DEREF` before any type check, or a reference slips past the check as the wrong type.

## Errors and exceptions

- In a `PHP_FUNCTION`/`PHP_METHOD` handler: throw with `zend_throw_exception_ex(...)` or `zend_argument_*_error(...)`, then **`RETURN_THROWS()` immediately**. Falling through after a throw runs code in an exception state.
- `RETURN_THROWS()` expands to a valueless `return`, so it is valid **only** in a void Zend handler. A `zend_result` helper that throws returns `FAILURE` (or its declared failure value) instead, and the handler translates that into `RETURN_THROWS()` at the boundary.
- After calling into userland (a callback, a magic method, `zend_call_function`), check three things in order: the call's own `zend_result`, then `EG(exception)`, then that the result zval is not `IS_UNDEF`. `zend_call_function` can return `FAILURE` without setting an exception, and it initializes the result to `IS_UNDEF`, so an exception check alone lets an undefined value through to be consumed or destroyed.
- Internal helpers return `zend_result`. Reserve `bool` for genuine predicates.
- A failed allocation does not return in the extension model: `emalloc` bails out with a fatal error. Do not write a NULL check that cannot fire. `pemalloc(size, 1)` does **not** restore a NULL return either, since it forwards to `__zend_malloc`, which calls `zend_out_of_memory()` on failure. When a recoverable, checkable allocation failure is genuinely required, drop to plain `malloc`/`free`. Use `safe_emalloc(nmemb, size, offset)` for the multiply-then-add case, which is about overflow-checked sizing, not recoverable failure.

## Macros that declare locals

A `RETURN_*`-style macro that declares its own `zend_string *s` shadows a `PHP_FUNCTION` parameter named `s`, so the macro's *argument* expression resolves against the macro's freshly-allocated buffer instead of the caller's input. The output is uninitialised heap, often a recycled previous result, so it is nondeterministic and a fixed `--EXPECT--` cannot pin it. Sanitizers stay silent because nothing is out of bounds.

Prefix macro internals so they cannot collide (`_ext_s`), and evaluate arguments into locals at the top before declaring anything. A round-trip identity `.phpt` (`from_bin(to_bin($x)) === $x`) catches this class instantly where an output-matching test cannot.

## C++ vendored libraries

An exception must never unwind into the Zend engine. Wrap every call into a C++ vendor library so the handler is a C-compatible boundary:

```c
try {
    vendor_call();
} catch (const std::exception &e) {
    zend_throw_exception(NULL, e.what(), 0);
    RETURN_THROWS();
} catch (...) {
    zend_throw_exception(NULL, "unknown error", 0);
    RETURN_THROWS();
}
```

The bare `catch (...)` is required: `catch (const std::exception &)` alone still lets a thrown `int`, a string literal, or a foreign exception type escape. For the general rules on C++/C boundaries, ABI stability, and symbol visibility, see the `ia-cpp-systems` skill.

## Memory

- `emalloc`/`efree`/`erealloc`: request-scoped, freed wholesale at request end. Default choice.
- `pemalloc(size, persistent)`/`pefree(ptr, persistent)`: survives the request. Anything that must outlive the request, including anything reachable from a persistent resource, has to be persistent-allocated.
- Request-scoped (`emalloc`) data may live in module globals, which is a standard pattern across php-src's own extensions, provided it is released **and the pointer reset** in `RSHUTDOWN`. What corrupts is a request-scoped pointer left in a global across requests: the next request reads freed memory.
- Never cross the allocators. `emalloc` pairs only with `efree`; `malloc` only with `free`.
- `zend_string` is refcounted: `zend_string_copy` to take a reference, `zend_string_release` to drop one. Interned strings have refcount handling of their own, so never `efree` a `zend_string` directly.
- `zval` ownership: `ZVAL_COPY` takes a reference, `ZVAL_COPY_VALUE` does not. `zval_ptr_dtor` on anything owned.
- A limit enforced by the request allocator counts only allocations that went through it. Bytes a bundled C library takes from `malloc(3)` are invisible to `memory_limit`, to the debug allocator, and to `memory_get_usage`, and no in-tree call installs an allocator hook for the XML stack. So any claim that `memory_limit` bounds an input-driven allocation is wrong wherever the bytes came from libxml, libxslt, GD, libzip, or ICU; the cap has to sit at the trust boundary, with an operating-system limit behind it. Parse and transform stages bypass it entirely, and only the copy back into a PHP string is ever counted.
- `RSHUTDOWN` is too early when the executor's own value teardown is what re-populates the container. A request-scoped table drained there can be refilled by a hook that runs afterwards, and `MSHUTDOWN` then reads memory the request pool has already released, which surfaces only under the tracked allocator because ordinary fast shutdown skips the per-value teardown entirely. `post_deactivate` is the hook that runs after the last producer and before the pool is freed. Destroy and reinitialize each table there rather than only draining it, so a re-entrant hook on a bailout path always meets a valid empty table instead of a half-freed one, and free the payloads first where the table carries no element destructor.

**Sanitizers need the Zend allocator disabled.** The pooling MM hides leaks and overflows from both ASan and Valgrind:

```bash
USE_ZEND_ALLOC=0 valgrind --leak-check=full php -d extension=modules/<ext>.so test.php
USE_ZEND_ALLOC=0 php ...          # with an -fsanitize=address build
```

This cuts one way only. A **clean** run with the pooling allocator enabled proves nothing, because the pool hides request leaks and allocator-local heap errors. A **positive** report is still a real finding: stack overflows, plain `malloc` misuse, invalid accesses that escape the pool, and unrelated UB all report accurately either way. Never dismiss a hit on the grounds that Zend MM was on.

## Custom objects

An object struct embeds `zend_object` **last**, and the handler offset is `offsetof(struct, std)`:

```c
typedef struct {
	/* fields first */
	zend_object std;
} ext_obj_t;
```

- Register handlers once in `MINIT`, copying `std_object_handlers` and overriding what changes.
- `free_obj` must call `zend_object_std_dtor` after releasing owned fields.
- A custom `create_object` without a matching `clone_obj` handler, or with `clone_obj` left pointing at the default, corrupts the heap on `clone`. Set it explicitly, including to NULL when cloning must be rejected.
- An abstract internal base is worth giving sentinel handlers that fail loudly, rather than leaving inherited ones that assume a concrete layout. Confirm the reachable paths against the engine version in use before relying on any specific one.

## Module globals

`ZEND_DECLARE_MODULE_GLOBALS(ext)` plus an accessor macro. Under ZTS the globals are per-thread, so never cache a raw pointer *to* a globals struct across requests or hand one to another thread; go through the accessor each time. Request-scoped contents are fine under the `RSHUTDOWN` discipline above.

## Assertions

`ZEND_ASSERT(cond)` compiles out unless the build is `--enable-debug`. It is the extension equivalent of the base skill's assert-density rule and carries the same zero release cost.

## Version compatibility

Guard on `PHP_VERSION_ID`, never on a runtime version string:

```c
#if PHP_VERSION_ID >= 80400
	/* 8.4+ path */
#endif
```

Keep the guard around the smallest region that differs. A guard wrapping a whole function duplicates the body and the two copies drift.

## Verify

- `make test` passes with zero `FAIL`, and any new `.phpt` fails without the change
- `USE_ZEND_ALLOC=0` run under Valgrind or ASan is clean
- `*_arginfo.h` matches a fresh `gen_stub.php` run
- No `emalloc`/`free` or `malloc`/`efree` crossing, and every request-scoped pointer in module globals is reset in `RSHUTDOWN`
- Every throw in a Zend handler is followed by `RETURN_THROWS()`; every throw in a `zend_result` helper returns `FAILURE` instead
- Every userland call checks its `zend_result`, then `EG(exception)`, then `IS_UNDEF`
- Every allocation sits below `ZEND_PARSE_PARAMETERS_END()`
