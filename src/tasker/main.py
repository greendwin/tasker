"""CLI entry point for tasker."""

from typing import Annotated, Optional

import typer

app = typer.Typer(
    name="tasker",
    help="File-based task tracker for git repos.",
    no_args_is_help=True,
)


@app.callback()
def _callback() -> None:
    pass


@app.command()
def hello(
    name: Annotated[Optional[str], typer.Argument(help="Name to greet.")] = None,
) -> None:
    """Say hello."""
    if name:
        typer.echo(f"Hello, {name}!")
    else:
        typer.echo("Hello, World!")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
