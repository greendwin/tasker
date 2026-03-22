import traceback
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import typer
from rich.console import Console

from ._exceptions import TaskerError


class OutputContext:
    debug: bool = False
    json_output: bool = False

    def __init__(self) -> None:
        self._console = Console()
        self._obj: dict[str, Any] = {}

    def print(self, text: str, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            self._obj[k] = v

        if not self.json_output:
            self._console.print(text)

    @contextmanager
    def catching_output(self) -> Iterator[None]:
        try:
            yield
        except TaskerError as ex:
            if not self.json_output:
                if self.debug:
                    raise
                console.print(f"[red]Error:[/red] {ex}")
                raise typer.Exit(1) from ex

            self._obj = {"error": str(ex)}
            if self.debug:
                self._obj["traceback"] = traceback.format_exc()
            raise typer.Exit(1) from ex
        except Exception as ex:
            if not self.json_output:
                raise

            self._obj = {
                "error": str(ex),
                "traceback": traceback.format_exc(),
            }
            raise typer.Exit(1) from ex
        finally:
            if self.json_output:
                self._console.print_json(data=self._obj)


console = OutputContext()
