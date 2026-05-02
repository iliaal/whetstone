## CLI Tools

**Entry points** in pyproject.toml:
```toml
[project.scripts]
my-tool = "my_package.cli:main"
```

**Click** (recommended for complex CLIs):
```python
import click

@click.group()
@click.version_option()
def cli(): ...

@cli.command()
@click.argument("name")
@click.option("--count", default=1, type=int)
def greet(name: str, count: int):
    for _ in range(count):
        click.echo(f"Hello, {name}!")

def main():
    cli()
```

**argparse** for simple CLIs -- subparsers for subcommands, `parser.add_argument("--output", "-o")`.

Use `src/` layout. Include `py.typed` for type hints. `importlib.resources.files()` for package data access.
