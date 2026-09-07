# Value and interface design

## Const correctness and value semantics

- `const` by default on locals, member functions, and reference parameters.
- Pass by value for types that are cheap to move (`std::string`, `std::vector`) when the function stores the argument; pass by `const&` when it only reads. Do not pass by `const&` and then copy inside.
- `std::string_view` for read-only string parameters, with one rule attached: never store one unless the backing buffer is guaranteed to outlive the view. A `string_view` member is a dangling reference waiting for a temporary.
- Mark member functions `const` and `noexcept` where true. `noexcept` on move operations is what lets `std::vector` move rather than copy on reallocation.


## Error handling

Pick one model per module and hold it at the boundary.

- **Exceptions** where the project allows them: throw types deriving from `std::exception`, throw by value, catch by `const&`. Use them for genuinely exceptional conditions, not for control flow.
- **`std::optional<T>`** for "absent is normal". **`std::expected<T, E>`** (C++23) or a project equivalent for "failed with a reason".
- **Error codes** in exception-free builds, with `[[nodiscard]]` on every returning function so an ignored failure is a warning.
- Mark anything that must not throw `noexcept`, and mean it: an escaping exception calls `std::terminate`.
- A constructor that can fail either throws or does not exist. Two-phase `init()` construction produces objects with an invalid state that every method must then check. Prefer a static factory returning `optional`/`expected`.


## API design

The decisions that break callers, learned the expensive way:

- **Three decisions break callers when they go wrong**: `explicit` on a single-argument constructor (decide at introduction, since adding it later is source-breaking), removing an overload (keep the narrow one and delegate), and an overload that silently ignores part of its argument (delete it or `static_assert` instead). Rationale and the full evolution rules are in the reference below.
- Prefer free functions over members where they do not need private access; they extend without touching the class.
- Return by value and let the compiler elide. Out-parameters exist for multiple returns and for reuse of a caller's buffer, not as an optimization.

For `extern "C"` boundaries, exception containment, PIMPL, and ABI-stable headers, load [api-and-abi.md](./api-and-abi.md).


## Templates and generic code

Use a template when at least three concrete instantiations exist or are certain. Before that, a concrete type is clearer and compiles faster.

- Constrain with C++20 concepts where available, `static_assert` plus type traits otherwise. An unconstrained template fails deep inside instantiation with an error nobody can read.
- `if constexpr` over tag dispatch and SFINAE where the standard allows it.
- Keep template definitions out of widely-included headers when the instantiation cost is real; explicit instantiation in one translation unit is often the right trade.
- Perfect forwarding (`T&&` plus `std::forward`) only in genuinely forwarding code. A forwarding reference in a constructor hijacks the copy constructor and produces baffling overload resolution.


## Standard library

- Prefer `<algorithm>` and ranges over hand-written loops; a named algorithm states intent that an index loop hides.
- `std::vector` unless measurement says otherwise. `reserve()` when the final size is known.
- Structured bindings for pair and tuple returns; a named struct for anything a caller will read twice.
- Use `std::move` only where the source is genuinely dead afterwards. Never depend on an *unspecified* post-move value; destroy, reassign, or invoke only operations whose post-move contract is documented. Some types do specify one (`unique_ptr` is null, `future` is invalid), and relying on those is fine.
- Never return `std::move(local)`: it defeats copy elision.
- Never call unknown code -- a user callback, a virtual, a comparator, a visitor -- from inside a loop over a container the callee can reach. Insertion invalidates iterators and pointers into the storage, and a callback that mutates the container being walked leaves the loop reading freed memory whose bytes usually still look plausible, so the first symptom is wrong output rather than a crash. Iterate a copy, or index by position and re-check `size()` after every reentrant call, and where elements are owned indirectly, take a strong reference on each one before the pass that can drop the last owner.
- A checked downcast per element is dispatch, not work. `dynamic_pointer_cast` from `shared_from_this()` costs an RTTI walk plus an atomic refcount round trip on a temporary, and in one rows-by-columns decode loop it measured about 18% of retired instructions. Where a type tag has already proved the concrete class, `static_cast` the raw pointer -- but keep the checked cast for any type whose tag-to-class mapping has moved across a library version, where the null return is the crash guard.
- An empty `std::string_view` may have `data() == nullptr`, which the standard permits, and `memcpy` declares its source non-null regardless of the size argument. Every libc no-ops a zero-length copy in practice, so the defect surfaces only as a UBSan diagnostic on each empty append. Guard the copy with a size check rather than suppressing the check.


## Legibility

Function decomposition, naming as a greppability contract, the name test that stops over-decomposition, contract comments, and a worked refactor with its change-cost proof: load [legibility-standard.md](./legibility-standard.md).
