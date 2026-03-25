from pathlib import Path
from typing import Annotated

import typer
from typer_di import TyperDI

from tasker.task_repo import TaskRepo
from tasker.utils import console

app = TyperDI(
    name="tasker",
    help="File-based task tracker for git repos.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)


@app.callback()
def common_options(
    debug: Annotated[
        bool, typer.Option("--debug", help="Show full tracebacks on errors.")
    ] = False,
    json_output: Annotated[
        bool, typer.Option("--json-output", help="Output result in json format.")
    ] = False,
) -> None:
    console.debug = debug
    console.json_output = json_output


def get_task_repo() -> TaskRepo:
    # TODO: this should be `.tasker` or configured using it
    planning = Path("planning")
    planning.mkdir(exist_ok=True)
    return TaskRepo(planning)
