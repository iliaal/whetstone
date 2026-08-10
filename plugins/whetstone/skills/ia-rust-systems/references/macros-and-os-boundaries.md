# Macro Hygiene and OS Boundaries

Two trap classes that type-check cleanly and fail at runtime or at a caller's crate. Load when authoring a `macro_rules!` or proc macro, or when touching filesystem paths, process output, or on-disk state.

## Declarative macros (`macro_rules!`)

These apply when *defining* a macro. An ordinary invocation of someone else's macro is not a site for any of them.

- **Interpolate an `$x:expr` fragment exactly once.** Each substitution re-evaluates the caller's expression, so `my_macro!(v.pop().unwrap())` runs the side effect once per mention. Bind it first inside the expansion (`let v = $x;`) and use the binding.
- **Reference items through `$crate`.** An exported macro expands in the *caller's* namespace, so a bare `helper()` or `Error` resolves against whatever the caller happens to have in scope. `$crate::helper()` binds to the defining crate regardless.
- **Parenthesize re-emitted `$t:tt` fragments.** A token-tree fragment is spliced verbatim, so `$a * $b` with `$a = 1 + 2` expands to `1 + 2 * b` and silently changes precedence. This does *not* apply to `:expr`, which is already parsed as one complete expression — wrapping those adds noise without preventing anything.
- **Do not assume identifier hygiene covers items.** Local variables introduced by an expansion are hygienic, but items (types, functions, consts) are not: two invocations in one module collide on any item the expansion names. Derive item names from a macro parameter, or emit them inside a generated module.

## Procedural macros

- **Emit `syn::Error` / `compile_error!`, never `panic!` or `unwrap()`.** A panic in a proc macro surfaces to the user as a compiler-internal failure with no source location. A `syn::Error` carries a span, so the error points at the offending token in their code.
- Compile the failure cases. `trybuild` fixtures for rejected input are the only way a macro's error contract stays honest through refactors.

## Paths and OS strings

- **`Path` is not UTF-8.** On Unix a filename is arbitrary bytes; on Windows it is potentially ill-formed UTF-16. `path.to_str().unwrap()` panics on filenames that are perfectly legal on the user's disk. Use `to_string_lossy()` where the value is only ever displayed, `OsStr`/`OsString` where it is passed through, and reserve `to_str()` for cases where non-UTF-8 is a genuine error the caller should see — with a real error, not an unwrap.
- The same applies to arguments and environment variables (`args_os()`, `var_os()`) when a value may originate outside the program.
- Subprocess output is bytes too. `String::from_utf8(output.stdout)` fails on any tool that emits non-UTF-8; decide deliberately between propagating that error and `from_utf8_lossy`.

## Crash-safe file updates

- **Write-then-rename.** Writing in place leaves a truncated file if the process dies mid-write, and the next run cannot distinguish it from a valid short file. Write to a temporary file in the *same directory* (rename is only atomic within a filesystem), then rename over the target.
- Persist the temporary explicitly rather than letting a `TempDir`/`NamedTempFile` guard delete it on the success path.
- Durability beyond the rename needs `sync_all()` on the file before renaming, and on the containing directory after, if the data must survive power loss rather than just process death. Skip both where the file is a rebuildable cache; state the choice either way.
- A retry after an interrupted update must be safe to run: the rename target either has the old content or the new one, never a blend.
