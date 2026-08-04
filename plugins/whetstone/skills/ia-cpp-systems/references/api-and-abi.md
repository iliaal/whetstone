# C++ API and ABI boundaries

Load when designing a public library header, exposing C++ to C, shipping a shared library other people link against, or changing anything already released.

## Exceptions must not cross an `extern "C"` boundary

`extern "C"` sets *language linkage*, not the caller's language: a C++ function with C linkage can still legally throw to a C++ caller. The reason to catch everything anyway is the contract. A C caller has no channel to receive a C++ exception, and unwinding through frames actually compiled as C is toolchain-dependent (GCC documents `-fexceptions` as sometimes necessary for exactly this). So every entry point of a C API converts:

```cpp
/* h and input must be non-NULL. On success *out_err is set to NULL.
 * On failure *out_err receives a message owned by the library; release
 * it with lib_error_free(). */
extern "C" int lib_do_thing(lib_handle *h, const char *input, char **out_err)
{
    if (out_err) *out_err = NULL;
    if (h == NULL || input == NULL)
        return LIB_ERR_ARG;

    try {
        reinterpret_cast<Impl *>(h)->doThing(input);
        return LIB_OK;
    } catch (const std::exception &e) {
        if (out_err) *out_err = lib_dup_message(e.what());
        return LIB_ERR;
    } catch (...) {
        if (out_err) *out_err = lib_dup_message("unknown error");
        return LIB_ERR;
    }
}
```

Three things that sample is doing deliberately. It states the non-NULL contract and enforces it, because a C caller gets no reference types to lean on. It clears `*out_err` on entry, so a caller that inspects it after success reads NULL rather than a stale pointer. And the message crosses the boundary through the library's own `lib_dup_message`/`lib_error_free` pair rather than `strdup`/`free`: the caller may link a different allocator, and whoever allocates must be whoever frees. `lib_dup_message` returning NULL under memory pressure is acceptable; the status code still reports the failure.

The bare `catch (...)` is not optional. A `catch (const std::exception &)` alone still lets an `int`, a string literal, or a foreign exception type escape.

The same rule applies to any callback a C library invokes: the callback body is a C frame boundary, so it catches everything and reports through the C API's error channel. This is the failure mode when wrapping a C++ vendor library from a C extension.

## `extern "C"` signature constraints

Only C-compatible types cross: fundamental types, pointers, and trivially-copyable structs with a stable layout. No references, no templates, no `std::` types, no default arguments, no overloading (there is no mangling to distinguish them).

Hand out an opaque pointer to the C++ object and a matching destroy function. `struct lib_handle;` declared but never defined in the public header prevents callers from dereferencing it.

## What breaks ABI

Once a shared library is released, all of the following break consumers even though they still compile. They break in three different ways, and the category decides how the break shows up.

**Layout breaks** — object size or member offsets are baked into already-compiled callers:

| Change | Why it breaks |
|---|---|
| Adding, removing, or reordering non-static data members | Size and offsets are compiled into callers |
| Adding the *first* virtual function | Adds a vtable pointer: changes size and layout |
| Adding to an existing vtable | Layout- and inheritance-model-dependent. Appending can preserve existing slots under narrow conditions, but never assume it; verify with an ABI diff tool |
| Changing a base class or its order | Shifts subobject offsets |
| Changing an enum's underlying type | Changes size and how it is passed |
| Changing alignment, packing, or a bitfield layout | Same as reordering |

**Symbol breaks** — whether the mangled name changes decides whether the break surfaces at link time:

| Change | Why it breaks |
|---|---|
| Changing parameter types or member-function `const`ness | Mangled name changes, so the old symbol disappears. **Loud**: callers fail to link |
| Changing only the return type | Itanium does not mangle an ordinary function's return type, so the symbol is unchanged and callers keep binding to it while disagreeing about what comes back. **Silent** |
| Adding or removing `noexcept` on a released function | Also absent from an ordinary function's mangled name. Callers compiled against the old spec may have omitted unwind handling. **Silent** |

**Semantic skew** — symbols and layout both survive, so nothing fails until a mixed-version deployment runs:

| Change | Why it breaks |
|---|---|
| Changing the body of an inline function | The old body is already inlined into callers |
| Changing a default argument value | Evaluated at the call site, not in the library |
| Changing an enum's numeric value | Callers embedded the old number |

The silent rows in the last two tables are the dangerous ones. A break that changes a mangled name announces itself; a break that preserves it ships. Run an ABI diff (`abi-compliance-checker`, `abidiff`) against the previous release rather than reasoning row by row.

Safe additions: new non-virtual, non-inline member functions; new free functions; new types; new overloads that do not displace existing ones.

## PIMPL when ABI stability is required

```cpp
// public header
class Client {
public:
    Client();
    ~Client();
    Client(Client &&) noexcept;
    Client &operator=(Client &&) noexcept;

    void connect(const char *host);

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
```

This hides `Impl`'s layout, so the implementation grows members freely. Be precise about what it does *not* hide: `Client` itself still has a visible layout of exactly one `unique_ptr`, and callers bake in that pointer's size and alignment. PIMPL therefore stabilizes `Client` only within a compatible compiler and standard-library ABI. Note the signature takes `const char *` rather than `const std::string &` for the same reason the section below gives; a `std::string` parameter would put a standard-library type straight into the boundary PIMPL exists to protect. For a genuinely cross-toolchain boundary, PIMPL is not enough: expose an opaque C handle with exported lifetime functions.

Two mechanics that trip people:

- The destructor must be **declared in the header and defined in the `.cpp`**, after `Impl` is complete. A defaulted destructor in the header fails to compile against an incomplete type.
- Move operations must be declared and defined in the `.cpp` for the same reason. Declaring the destructor already suppressed the implicit ones.

Cost: one allocation per object and one indirection per call. Pay it at a stable library boundary, not on an internal type.

## Standard library types in a public ABI

Do not expose `std::string`, `std::vector`, or any other standard container by value or by reference across a shared-library boundary that consumers may build differently. Their layout varies with standard library implementation, `_GLIBCXX_USE_CXX11_ABI`, libstdc++ debug mode (`_GLIBCXX_DEBUG`), MSVC's `_ITERATOR_DEBUG_LEVEL`, and standard version.

How a mismatch surfaces depends on where the type appears. When it is part of a mangled signature, `_GLIBCXX_USE_CXX11_ABI` mismatches are link errors *by design* — that is the entire purpose of the `std::__cxx11` inline namespace and `abi_tag`. The silent case is the one to fear: a standard type embedded in a user struct, or crossing an opaque boundary such as a `void *` or a plugin interface, where nothing forces the mangled names to disagree and the layouts simply differ. Note also that `_GLIBCXX_ASSERTIONS` is libstdc++'s hardening macro and is documented as ABI-neutral; `_GLIBCXX_DEBUG` is the one that changes layout.

At a hard boundary, pass `const char *` plus length, or a trivially-copyable struct the library owns. Inside one build unit, or in a header-only library the consumer compiles with their own flags, the standard types are fine.

Throwing exceptions across a shared library boundary requires consistent RTTI and typeinfo, which means one compiler and one standard library. Never do it across a plugin boundary the host might have built differently.

## Symbol visibility

Default visibility exports every symbol, which bloats the dynamic symbol table, slows load time, and turns internal helpers into an accidental API nobody can change.

```cmake
set_target_properties(mylib PROPERTIES
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN ON)
```

Then mark the public surface explicitly:

```cpp
#if defined(_WIN32)
#  define LIB_API __declspec(dllexport)
#else
#  define LIB_API __attribute__((visibility("default")))
#endif

class LIB_API Client { /* ... */ };
```

Generate this with CMake's `generate_export_header` rather than hand-rolling the import and export halves.

## API evolution that does not break callers

- **Decide `explicit` at introduction.** Adding it later is source-breaking: every call site relying on the implicit conversion stops compiling. Removing it later is safe but widens the API permanently.
- **Keep an overload when adding a better one.** Delegate the old to the new. Deleting an overload breaks callers even when a superset exists.
- **Delete rather than silently ignore.** When an overload cannot honor part of an argument's state, `= delete` it or `static_assert`, so the caller learns at compile time instead of filing a bug that the feature does nothing.
- **`[[deprecated("use X instead")]]`** for one release before removal, and only where a replacement exists.
- **Inline namespaces** (`inline namespace v2 { ... }`) version an entire API surface within one library, so old and new symbols coexist and mismatches are link errors rather than corruption.

## Verify

- Every `extern "C"` entry point has a `catch (...)`
- No `std::` type crosses a shared-library boundary consumers build themselves
- PIMPL destructor and move operations defined in the `.cpp`, not defaulted in the header
- Visibility is hidden by default with an explicit export macro on the public surface
- For a released library: `abi-compliance-checker` or an equivalent diff against the previous release shows no incompatible change
