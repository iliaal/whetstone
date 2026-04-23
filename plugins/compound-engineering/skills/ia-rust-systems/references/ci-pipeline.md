# Rust CI Pipeline — language-specific callouts

Load this reference when setting up or reviewing a CI pipeline for a Rust project. General CI design (matrix strategy, caching, deployment gating) lives with the `ia-infrastructure-engineer` agent — this file covers only the Rust-specific pieces.

- **`rustsec/audit-check`** — runs `cargo audit` against the RustSec Advisory DB. Catches published CVEs in your dependency graph. Wire it as a required PR check, not a nightly job; advisory hits on `main` are already too late.
- **Coverage via `cargo-llvm-cov`** — `cargo llvm-cov --workspace --lcov --output-path lcov.info` produces codecov-compatible output without the instrumentation overhead of `tarpaulin`. Prefer it for any new Rust project.
- **`Swatinem/rust-cache`** — caches `~/.cargo/registry`, `~/.cargo/git`, and `target/` keyed on `Cargo.lock`. Cuts cold-CI time from ~5min to ~90s on typical workspaces. Install before cargo commands.
- **`taiki-e/install-action`** — fast binary installer for cargo tools (nextest, llvm-cov, audit). Faster than `cargo install` on CI by orders of magnitude.
- **Matrix coverage**: at minimum `stable` on Linux. Add `beta` + `nightly` on Linux and `stable` on Windows + macOS if the crate is a library others consume; skip the full OS matrix for internal services.
- **Doc tests**: `cargo test --doc --all-features` as a separate step. Doc tests are easy to break with a refactor and easy to miss with `nextest run` alone.
