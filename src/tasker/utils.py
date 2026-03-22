from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

import typer
from rich.console import Console

from ._exceptions import TaskerError

console = Console()


@dataclass
class ErrorReporter:
    debug: bool = False

    @contextmanager
    def catch_errors(self) -> Iterator[None]:
        try:
            yield
        except TaskerError as ex:
            if self.debug:
                raise
            console.print(f"[red]Error:[/red] {ex}")
            raise typer.Exit(1) from ex


error_reporter = ErrorReporter()
