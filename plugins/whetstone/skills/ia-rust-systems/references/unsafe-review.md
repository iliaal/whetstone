# Reviewing unsafe Rust

Read before writing or reviewing `unsafe` blocks, `unsafe fn`, `unsafe impl`, or FFI wrappers. A `// SAFETY:` comment is a claim to check against the code, not evidence. Each check below names a pattern that passes a comment-presence review, and often a Miri run over the tested paths, while still being unsound.

## 1. Give every site one disposition

List every site (`rg -n '\bunsafe\b'`, plus `extern` blocks and `#[no_mangle]` / `#[unsafe(no_mangle)]` exports) and record exactly one disposition per site:

| Disposition | Record |
|---|---|
| Sound | Each premise of the operation's contract and the code (type, bound, dominating check, caller `# Safety` contract) that enforces it |
| Candidate | The premise no code enforces and an input that breaks it |
| Excluded | Why the site is out of scope (generated code, test-only helper, vendored crate under its own review) |
| Duplicate | The site it repeats, by `file:line` |

Do not sample. A review that reads the first few hits and generalizes reports itself as incomplete and names the sites it did not reach.

## 2. Creating a reference from raw parts is the unsafe operation

`&*ptr`, `&mut *ptr`, `slice::from_raw_parts`, `Box::from_raw`, and `Pin::new_unchecked` assert their premises at the moment of creation, not when the value is first read. At that moment the pointer must be non-null, aligned for the target type, inside one live allocation that covers the whole value, initialized to a valid value of the type, and free of conflicting borrows for the whole lifetime the reference gets (no `&mut` overlapping any other live reference). A reference created and never used is still undefined behavior when a premise fails.

Reject (length, alignment, and validity all unchecked; `&[u8]` guarantees alignment 1 only):

```rust
fn header(bytes: &[u8]) -> &Header {
    // SAFETY: bytes holds a header.
    unsafe { &*bytes.as_ptr().cast::<Header>() }
}
```

Accept (each premise is checked in code, or holds by the type definition):

```rust
#[repr(C)]
struct Header {
    magic: u32,
    len: u32,
}

fn header(bytes: &[u8]) -> Option<&Header> {
    if bytes.len() < size_of::<Header>() {
        return None;
    }
    let p = bytes.as_ptr().cast::<Header>();
    if !p.is_aligned() {
        return None;
    }
    // SAFETY: p is non-null and aligned (checked above) and covers size_of::<Header>()
    // initialized bytes borrowed from `bytes` for the returned lifetime; Header has only
    // integer fields, so every bit pattern is a valid Header.
    Some(unsafe { &*p })
}
```

Prefer `zerocopy` or `bytemuck`, whose derives prove the layout and validity premises at compile time, over the hand-written form.

## 3. A zero-length slice still needs a non-null, aligned pointer

`slice::from_raw_parts(ptr, 0)` with a null or misaligned `ptr` is undefined behavior; the length does not waive the pointer premises. C APIs commonly return `(NULL, 0)` for an empty result. The total size `len * size_of::<T>()` must also not exceed `isize::MAX`.

Reject:

```rust
// SAFETY: the C API returns ptr/len for a valid buffer.
let items = unsafe { std::slice::from_raw_parts(raw.ptr, raw.len) };
```

Accept:

```rust
let items: &[Item] = if raw.len == 0 {
    &[]
} else {
    assert!(!raw.ptr.is_null(), "C API returned NULL for a non-empty result");
    // SAFETY: the API contract guarantees raw.ptr points to raw.len initialized,
    // aligned Items that stay valid until `raw` is freed, which outlives `items`.
    unsafe { std::slice::from_raw_parts(raw.ptr, raw.len) }
};
```

When a raw pointer is needed for an empty buffer, use `NonNull::dangling()`, not null.

## 4. Equal size does not justify `transmute`

`transmute` checks only that the two sizes match at compile time. The result must also be a valid value of the target type:

- **Validity.** `bool` is only 0 or 1; `char` excludes surrogates and values above `0x10FFFF`; an enum holds only its declared discriminants; references and `NonZero*` are never zero.
- **Niches.** `Option<&T>`, `Option<NonZeroU32>`, and `Option<Box<T>>` use the forbidden value as `None`, so writing a raw bit pattern into one can produce a `Some` that dangles.
- **Padding.** Transmuting a struct with padding into `[u8; N]` reads uninitialized bytes, which is undefined behavior.
- **Layout.** `repr(Rust)` layout is unspecified, so two structs with the same field list are not guaranteed to share a layout.
- **Lifetimes.** `transmute` silently extends a lifetime; a transmute between two reference types can hand out a borrow that outlives its owner.

Reject (any byte other than 0 or 1 produces an invalid enum):

```rust
#[repr(u8)]
enum Kind {
    A = 0,
    B = 1,
}

let kind: Kind = unsafe { std::mem::transmute(byte) };
```

Accept:

```rust
impl TryFrom<u8> for Kind {
    type Error = u8;

    fn try_from(b: u8) -> Result<Self, u8> {
        match b {
            0 => Ok(Kind::A),
            1 => Ok(Kind::B),
            other => Err(other),
        }
    }
}
```

## 5. Rely on a sealed trait only when downstream cannot implement it

Unsafe code that trusts a trait's methods or constants (a size, an alignment, a bound) is sound only if every implementation is under the crate's control. A sealed trait is one whose supertrait downstream code cannot name or satisfy. The seal leaks through a blanket impl over a public trait, a public macro that emits impls, a `#[doc(hidden)] pub` path to the supertrait, or a re-export.

Reject (the blanket impl lets any downstream type that implements `AsRef<[u8]>` satisfy `Sealed`, and then implement `Pixel` with any `BYTES`):

```rust
mod private {
    pub trait Sealed {}
}

pub trait Pixel: private::Sealed {
    const BYTES: usize;
}

impl<T: AsRef<[u8]>> private::Sealed for T {}
```

Accept: implement `Sealed` only for concrete crate types (`impl private::Sealed for Rgb8 {}`), or declare the trait `pub unsafe trait Pixel` with a `# Safety` section stating the contract implementors must uphold, or check the trusted value at each use instead of relying on it.
