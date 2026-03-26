from pathlib import Path
from typing import Annotated

import typer
from typer_di import TyperDI

from tasker.base_types import Task
from tasker.exceptions import TaskArchivedError
from tasker.repo import TaskRepo
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


def resolve_ref(repo: TaskRepo, task_ref: str) -> Task:
    """Resolve a task ref, reporting archived tasks in human-friendly format."""
    try:
        return repo.resolve_ref(task_ref)
    except TaskArchivedError as ex:
        if console.json_output:
            raise

        console.print(f"[yellow]Task [blue]{ex.task_ref}[/blue] is archived.[/yellow]")
        console.print("Unarchive it first before performing actions on it.")
        raise typer.Exit(1) from ex
