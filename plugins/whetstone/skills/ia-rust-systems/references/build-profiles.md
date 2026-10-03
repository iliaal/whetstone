# Build Profiles

Load this reference when setting up or tuning a Rust project's Cargo build profiles. Tune profiles for the shape of the binary: defaults ship fast debug builds and modest-optimization release builds, but application Rust benefits from more aggressive profiles.

## Profile definitions (Cargo.toml)

```toml
# Production release with task/request panic recovery
[profile.release]
lto = "fat"           # Link-time optimization across all crates
codegen-units = 1     # Single codegen unit trades compile time for runtime perf
strip = true          # Strip symbols from the final binary
panic = "unwind"

# Release with symbols kept for profiling (perf, flamegraph, pprof)
[profile.release-dbg]
inherits = "release"
strip = false
debug = true

# Size-minimized release for distributable CLIs
[profile.release-min]
inherits = "release"
opt-level = "z"       # Optimize for size over speed
```

Keep `panic = "unwind"` when a task boundary or `catch_unwind` must convert a panic into an error response. Choose `panic = "abort"` only when immediate process termination is the intended failure policy; Tokio cannot return a panic as `JoinError` after the process aborts. Panic hooks run in both modes and provide diagnostics, not recovery. Select panic policy at the final application's profile rather than promising recovery from a library's profile setting.

## Dev-machine compile speedups (.cargo/config.toml)

Cut PR compile time on Linux with mold:

```toml
[build]
rustflags = ["-C", "link-arg=-fuse-ld=mold"]

[target.x86_64-unknown-linux-gnu]
rustflags = [
    "-C", "link-arg=-fuse-ld=mold",
    "-C", "target-cpu=native",   # dev machines only — bakes in CPU features
    "-Z", "share-generics=y",    # share monomorphizations across crates (nightly)
]

[alias]
t = "nextest run"
```

Mold is Linux-only (`lld` on other platforms). `target-cpu=native` is a developer-machine convenience; remove for reproducible CI and distributable binaries.
