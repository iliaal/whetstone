# Rust CLI Tools

Patterns for building agent-friendly, scriptable CLIs with `clap`.

## Project Layout

```
src/
  main.rs       # CLI parse + dispatch only, no business logic
  cli.rs        # clap structs and enums
  commands/
    mod.rs
    index.rs    # one handler per subcommand
    search.rs
  config.rs     # TOML/env loading, validation
  output.rs    # JSON / human formatters
Cargo.toml
```

Keep `main.rs` under 20 lines. Every subcommand is a free function that takes parsed args + shared state and returns `Result<()>`. This makes each command independently testable.

## Clap Derive Patterns

```rust
use clap::{Parser, Subcommand, Args};

#[derive(Parser)]
#[command(name = "myapp", version, about)]
struct Cli {
    #[command(flatten)]
    global: GlobalOpts,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Args)]
struct GlobalOpts {
    /// Increase logging verbosity (-v, -vv, -vvv)
    #[arg(short, long, global = true, action = clap::ArgAction::Count)]
    verbose: u8,

    /// Emit JSON instead of human output
    #[arg(long, global = true)]
    json: bool,
}

#[derive(Subcommand)]
enum Commands {
    /// Index the current project
    Index(IndexArgs),
    /// Search the index
    Search(SearchArgs),
}
```

- `global = true` flags apply to every subcommand without repeating.
- Use `value_enum` for typed string flags:
  ```rust
  #[arg(long, value_enum, default_value_t = Format::Md)]
  format: Format,
  ```
- `#[arg(value_parser = validate_path)]` to reject bad values before the handler runs.

## Layered Parsing for Non-Trivial CLIs

Once flag count crosses ~10 or commands start sharing complex validation, split parsing into two stages:

1. **Low stage** — `LowArgs` mirrors the raw CLI surface 1:1. Clap populates it. No cross-field validation, no domain types.
2. **High stage** — `HiArgs` (or `Config`) is what the rest of the program consumes. Constructing `HiArgs::from(low)` runs *all* semantic validation: mutual exclusions, path existence, glob compilation, range constraints, regex validity. Fails with one clear error message.

```rust
let low = Cli::parse();
let hi = HiArgs::try_from(low).context("invalid arguments")?;
run(hi).await
```

Downstream code accepts `&HiArgs` (or specific typed fields from it) and never re-checks. This keeps validation in one place and makes it impossible for a handler to receive an invalid combination. Pattern comes from ripgrep; worth it as soon as flag interactions become non-trivial.

For simple CLIs (one subcommand, a handful of flags), skip this — one clap-derive struct is enough.

## Config Layering

Priority (lowest to highest): built-in defaults → `~/.config/myapp/config.toml` → project `.myapp/config.toml` → env vars (`MYAPP_*`) → CLI flags.

Use `figment` or hand-roll with `serde` + `toml`:

```rust
#[derive(Deserialize, Debug)]
pub struct Config {
    #[serde(default = "default_limit")]
    pub limit: usize,
    pub api_key: Option<String>,
}

impl Config {
    pub fn load(project_root: &Path) -> Result<Self> {
        let mut cfg: Config = toml::from_str(
            &std::fs::read_to_string(project_root.join(".myapp/config.toml"))
                .unwrap_or_default(),
        )?;
        if let Ok(key) = std::env::var("MYAPP_API_KEY") {
            cfg.api_key = Some(key);
        }
        cfg.validate()?;
        Ok(cfg)
    }
}
```

Validation runs in `load()` — never defer it to the first call site.

## Logging

```rust
use tracing_subscriber::{EnvFilter, fmt};

fn init_logging(verbose: u8) {
    let level = match verbose {
        0 => "warn",
        1 => "info",
        2 => "debug",
        _ => "trace",
    };
    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new(format!("myapp={level}")));
    fmt().with_env_filter(filter).with_writer(std::io::stderr).init();
}
```

- Logs go to **stderr**. Only command results go to stdout. This keeps pipes clean.
- Respect `RUST_LOG` / `MYAPP_LOG` env var if set — it overrides `-v`.
- Never log at `info!` inside hot loops; budget is roughly one log line per user-visible action.

## Output

Every query command supports two modes:

```rust
if args.json {
    println!("{}", serde_json::to_string(&results)?);
} else {
    render_human(&results);
}
```

- JSON output must be a single line or a valid JSON document — no mixed human + JSON in the same stream.
- Exit with non-zero on failure even when `--json` is set; don't emit `{"error": "..."}` with exit 0.

## Progress

- Interactive terminals (check `std::io::IsTerminal::is_terminal(&stderr)`): `indicatif` progress bars on stderr.
- Non-interactive (pipes, CI, agents): plain periodic log lines. Never emit control codes to a non-tty.
- `--quiet` flag suppresses both.

## Shell Completions

```rust
use clap_complete::{generate, Shell};

Commands::Completions { shell } => {
    let mut cmd = Cli::command();
    generate(shell, &mut cmd, "myapp", &mut std::io::stdout());
}
```

Ship completions via the `completions` subcommand rather than pre-generated files — keeps them in sync with the actual flag set.

## Testing CLIs

```rust
use assert_cmd::Command;
use predicates::prelude::*;

#[test]
fn search_returns_json() {
    Command::cargo_bin("myapp").unwrap()
        .args(["search", "foo", "--json"])
        .assert()
        .success()
        .stdout(predicate::str::starts_with("["));
}
```

- `tempfile::TempDir` for isolated project roots.
- Snapshot stdout with `insta::assert_snapshot!` for human-readable output that changes rarely.
- Test exit codes explicitly — they're part of the CLI contract for scripts.

## Common Traps

- Don't print to stdout from library crates. Return structured data, let the binary format it.
- Don't swallow `SIGPIPE`. On Unix, when the reader closes a pipe early, the default is to die — let it. If you install a `tokio::signal` handler, re-raise or exit cleanly on pipe errors.
- Don't ship a CLI that panics on bad input. Map every user-facing error to a clean `anyhow` chain with `.context()`.
