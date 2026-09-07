# Tooling and tests

## Modern Tooling

| Tool | Replaces | Purpose |
|------|----------|---------|
| **uv** | pip, virtualenv, pyenv, pipx | Package/dependency management |
| **ruff** | flake8, black, isort | Linting + formatting |
| **ty** | mypy, pyright | Type checking (Astral, faster) |

- `uv init --package myproject` for distributable packages, `uv init` for apps
- `uv add <pkg>`, `uv add --group dev <pkg>`, never edit pyproject.toml deps manually
- `uv run <cmd>` instead of activating venvs -- auto-activates the venv without explicit activation
- `uv add --upgrade <pkg>` to upgrade a single package without touching others
- `uv tree --outdated` to preview what would be upgraded before committing
- `uv.lock` goes in version control
- uv treats an exactly-pinned (`==`) yanked transitive version as unsolvable; plain `pip` only warns and installs it. If a dependency hard-pins a yanked release (and bumping the leaf won't help because the pin is exact), `uv pip install` fails resolution where a pip-based script stays green. Drop the package from the requirements you feed uv when it's off your code path; fall back to `pip` only when the path genuinely needs it
- A user-level `~/.config/uv/uv.toml` carrying `exclude-newer` is serialized into `uv.lock` as an `[options]` block, and a clean CI runner with no matching global policy then rejects the committed lock: `Ignoring existing lockfile due to removal of global exclude newer`, followed by `uv sync --locked` failing. Pinning CI to the same uv version does not fix it -- the difference is configuration, not resolver. Generate repository locks with `uv --no-config lock` and spell canonical commands `uv --no-config sync --locked` / `uv --no-config run …`; strip any inherited `[options]` `exclude-newer` from the committed lock and add a contract test that rejects those entries and pins the `--no-config` command shape, or a later local regeneration reintroduces the CI failure silently
- Use `[dependency-groups]` (PEP 735) for dev/test/docs, not `[project.optional-dependencies]`
- PEP 723 inline metadata for standalone scripts with deps
- `ruff check --fix . && ruff format .` for lint+format in one pass

**Standard project layout:**
```
src/mypackage/
    __init__.py
    main.py
    services/
    models/
tests/
    conftest.py
    test_main.py
pyproject.toml
```

See [cli-tools.md](./cli-tools.md) for Click patterns, argparse, and CLI project layout.


## Testing Patterns

- **pytest flags**: `--lf` (last failed), `-x` (stop on first failure), `-k "pattern"` (filter), `--pdb` (debugger on failure)
- **Fixtures**: use `conftest.py` for shared fixtures. Scope wisely: `@pytest.fixture(scope="session")` for expensive setup (DB connections), `scope="function"` (default) for test isolation
- **`tmp_path`**: built-in fixture for temp files -- no manual cleanup needed
- **Parametrize with IDs**: `@pytest.mark.parametrize("input,expected", [...], ids=["empty", "single", "overflow"])` for readable test names
- **Mock discipline**: always `autospec=True` on mocks to catch API drift. `assert_awaited_once()` for async mocks.
- **Test markers**: register in `pyproject.toml` under `[tool.pytest.ini_options]` with `markers = ["slow", "integration"]`. Run fast tests with `-m "not slow"`.
- **Protocol duck typing**: use `class Renderable(Protocol)` for structural typing at service boundaries -- enables testing with plain objects instead of mocks
- **Context managers**: `@contextmanager` for connection/transaction lifecycle. Always implement `__exit__` cleanup.
- **A package `__init__.py` that eager-imports a heavy stack defeats every in-test skip guard.** Under pytest's default `prepend` import mode, importing `pkg.test_foo` imports `pkg` first and runs its `__init__.py` before any line of the test module executes -- so `pytest.importorskip(...)` and a module-level `pytest.skip(allow_module_level=True)` are both dead code, and a `conftest.py` *inside* the package imports as `pkg.conftest` and fails identically. `collect_ignore`/`collect_ignore_glob` prune directory *recursion* and are **not** honored for paths named explicitly on the command line, so they cannot skip a broken file either. There is no clean in-test-file option once `__init__` is the failing layer: make the package `__init__` lazy (the real fix, but it touches production code), drop `__init__.py` from the test directory so a module-level guard can run, or scope `testpaths` so a bare `pytest` never collects it -- and document the limitation in the test docstring rather than shipping a guard that cannot fire.
