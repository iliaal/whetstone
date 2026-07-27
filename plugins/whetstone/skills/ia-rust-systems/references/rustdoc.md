# Rustdoc Discipline

Doc comments are compiled artifacts, not prose decoration. `cargo test --doc` builds and runs every fenced example, so a stale doc example fails CI the same way a stale unit test does.

## Which comment form

| Form | Documents | Placement |
|------|-----------|-----------|
| `///` | The item that follows | Above `pub fn`, `pub struct`, `pub enum`, `pub trait`, fields, variants |
| `//!` | The enclosing item | First lines of `lib.rs`, `main.rs`, or a `mod.rs` |

Write `//!` on `lib.rs` to answer "what is this crate for and where does a caller start". Write `///` on every public item to answer "what does this do, what does it take, what comes back".

## Required sections

Use these headings when they apply — clippy's `missing_errors_doc`, `missing_panics_doc`, and `missing_safety_doc` lints check for exactly these:

```rust
/// Parses a config file into a validated `Config`.
///
/// # Examples
///
/// ```
/// # use mycrate::Config;
/// let cfg = Config::parse("timeout = 30")?;
/// assert_eq!(cfg.timeout.as_secs(), 30);
/// # Ok::<(), mycrate::Error>(())
/// ```
///
/// # Errors
///
/// Returns [`Error::Syntax`] if the input is not valid TOML, and
/// [`Error::Validation`] if a field is out of range.
///
/// # Panics
///
/// Panics if called after `Config::freeze` has run on the same thread.
pub fn parse(input: &str) -> Result<Config, Error> { /* ... */ }
```

- `# Examples` — at minimum on every public entry point. Lines prefixed `#` are compiled but hidden from rendered output, which keeps imports and error plumbing out of the reader's way.
- `# Errors` — what each error variant means, not just "returns an error".
- `# Panics` — every reachable panic, including `unwrap` on an invariant the caller could violate.
- `# Safety` — mandatory on every `pub unsafe fn`: the invariants the caller must uphold.

## Enforcement

```rust
// lib.rs
#![deny(missing_docs)]
```

Workspace-wide, prefer the centralized form so members can't drift:

```toml
[workspace.lints.rust]
missing_docs = "deny"

[workspace.lints.rustdoc]
broken_intra_doc_links = "deny"
private_intra_doc_links = "warn"
```

`broken_intra_doc_links` is the one that pays for itself — `[`Config::parse`]` links silently rot on rename, and nothing else catches it.

## Verify

- `cargo doc --no-deps --all-features` emits zero warnings
- `cargo test --doc --all-features` passes
- Public items added in the change carry `///` with the sections that apply

Binary crates can skip `missing_docs`; library crates and any crate published to a registry should not.
