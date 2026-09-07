# Toolchain and public interfaces

## Tooling

| Tool | Purpose |
|------|---------|
| `cargo` | Build, dep management, script runner |
| `clippy` | Lint (`cargo clippy --workspace --all-targets -- -D warnings`) |
| `rustfmt` | Formatter (`cargo fmt --all`) |
| `cargo-nextest` | Test runner |
| `cargo-deny` | License + advisory + duplicate-dep checks |
| `cargo-machete` | Find unused dependencies |

- Pin `rust-toolchain.toml` per repo so every contributor and CI uses the same compiler.
- `cargo update -p <crate>` for single-package upgrades. `cargo update` rewrites everything — avoid in PR diffs.
- `Cargo.lock` goes in version control for binaries *and* libraries (modern guidance; reproducibility wins).
- `cargo install <crate>` from a registry or git source no-ops silently when the installed version matches — it prints "package is already installed" and keeps the old binary; pass `--force` in install scripts. `cargo install --path .` always rebuilds and replaces regardless of `--force`. Either way, certify the **installed** artifact (`which <bin>` + version/behavior probe), not `target/release/<bin>` — the two can diverge when a stale env override points tests at the wrong one.
- **A crate's default feature set can encode a runtime ABI floor**, and a version bump can move it. For a crate that loads a system library dynamically, the API-level feature is the contract demanded of the `.so` at load time; compilation never opens that library, so a green build proves nothing and the failure arrives as a version rejection at first use. Pin `default-features = false` plus the explicit API-level feature the installed runtime provides, add the target features back by name, and assert the compiled-against version constant in a test. A floor is a minimum — a newer runtime still serves the older table.


## Workspaces

Multi-crate projects use a workspace with layered crates. Dependencies point inward only.

```
Cargo.toml                  # [workspace] members + [workspace.dependencies]
crates/
  protocol/    # Shared types, no deps on other workspace crates
  storage/     # Persistence, depends on protocol
  service/    # Business logic, depends on protocol + storage
  cli/        # Binary, depends on everything
```

- Centralize versions in `[workspace.dependencies]`, reference as `foo = { workspace = true }` in members.
- Keep the leaf-most crate (`protocol` / types) dependency-free so every other crate can depend on it without cycles.
- Feature flags belong on the crate that introduces the dependency, not re-exported through the workspace root.
- **Library crates expose one stable facade**: a thin `lib.rs` with a `//!` purpose doc and `pub use` re-exports — one import path per concept, internals free to reorganize without breaking callers.
- **`pub` alone does not prove an item is externally reachable.** Reachability runs through the re-export graph: a `pub` item inside a private module that is never re-exported is free to change, while the same item surfaced through a `pub use` at the crate root is not — even though its containing module stays private. (A `pub(crate)` item cannot be re-exported *outside* the crate: `pub use` on one is `E0364`, while `pub(crate) use` compiles.) Trace the facade before calling a reorganization internal. On a library crate with a published baseline, `cargo semver-checks` settles it mechanically.
- **Defining a `macro_rules!` or proc macro, or handling paths, process output, or on-disk state?** Load [macros-and-os-boundaries.md](./macros-and-os-boundaries.md) — `$crate` resolution, single-interpolation of `$x:expr`, `$t:tt` precedence, item-name collisions across invocations, `syn::Error` over panic, non-UTF-8 `Path`/`OsStr`, and write-then-rename. These type-check cleanly and fail on a caller's machine.
- **Document public items at the point of exposure.** `///` on every public item (purpose, params, return, plus `# Examples` / `# Errors` / `# Panics` / `# Safety` where they apply); `//!` for modules and crates. Doc examples compile and run under `cargo test --doc`, so they are regression tests, not decoration. Enforce with `#![deny(missing_docs)]` on library crates; see [rustdoc.md](./rustdoc.md).
- **Feature gates must error, never silently degrade.** If runtime config requests a capability the binary wasn't compiled with (e.g. `device = "gpu"` on a non-CUDA build), fail at startup — silent fallback diverges from operator config unnoticed.
- **Centralize lints at the workspace root** with `[workspace.lints.*]` — every member crate inherits the same ruleset, no per-crate `#![deny(...)]` drift:

  ```toml
  [workspace.lints.clippy]
  all = { level = "warn", priority = -1 }
  pedantic = { level = "warn", priority = -1 }
  ```

  Each member crate opts in with `[lints] workspace = true`.


## Build Profiles

When tuning Cargo build profiles (release LTO, release-dbg symbols, release-min for distributable binaries) or adding dev-machine speedups (mold linker, `target-cpu=native`, share-generics), load [build-profiles.md](./build-profiles.md).


## CI

General CI design lives with the `ia-infrastructure-engineer` agent. For Rust-specific callouts (`rustsec/audit-check`, `cargo-llvm-cov`, `Swatinem/rust-cache`, `taiki-e/install-action`, matrix coverage guidance, doc-test step), load [ci-pipeline.md](./ci-pipeline.md).
