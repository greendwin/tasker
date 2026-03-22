import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from typer_di import Depends, TyperDI

from tasker.methods import TaskerConfig, add_subtask, create_new_story, ref_to_task_id
from tasker.utils import console

app = TyperDI(
    name="tasker",
    help="File-based task tracker for git repos.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)


@app.callback()
def _callback(
    debug: Annotated[
        bool, typer.Option("--debug", help="Show full tracebacks on errors.")
    ] = False,
    json_output: Annotated[
        bool, typer.Option("--json-output", help="Output result in json format.")
    ] = False,
) -> None:
    console.debug = debug
    console.json_output = json_output


def get_config() -> TaskerConfig:
    planning = Path("planning")
    planning.mkdir(exist_ok=True)
    return TaskerConfig(root_dir=planning)


@app.command("new")
def new_task(
    *,
    title: Annotated[str, typer.Argument(help="Task title.")],
    details: Annotated[
        Optional[str], typer.Option("--details", "-d", help="Task description.")
    ] = None,
    slug: Annotated[
        Optional[str], typer.Option("--slug", help="Override auto-derived slug.")
    ] = None,
    extended: Annotated[
        bool, typer.Option("--extended", help="Create task as a directory.")
    ] = False,
    config: TaskerConfig = Depends(get_config),
) -> None:
    with console.catching_output():
        task_id = create_new_story(
            config, title=title, description=details, slug=slug, extended=extended
        )
        console.print(
            f"[green]task [blue]{task_id}[/blue] created[/green]",
            json_output={"task_id": task_id},
        )


@app.command("add")
def add_task(
    *,
    parent_ref: Annotated[str, typer.Argument(help="Parent task ID.")],
    title: Annotated[str, typer.Argument(help="Subtask title.")],
    config: TaskerConfig = Depends(get_config),
) -> None:
    with console.catching_output():
        task_id = ref_to_task_id(parent_ref)
        child_id = add_subtask(config, task_id=task_id, title=title)
        console.print(
            f"[green]task [blue]{child_id}[/blue]"
            f" added to [blue]{task_id}[/blue][/green]",
            json_output={"task_id": child_id},
        )


@app.command("add-many")
def add_many_tasks(
    *,
    parent_ref: Annotated[str, typer.Argument(help="Parent task ID.")],
    config: TaskerConfig = Depends(get_config),
) -> None:
    with console.catching_output():
        task_id = ref_to_task_id(parent_ref)
        console.print(
            f"[blue]Adding tasks to {task_id}[/blue] (empty line to finish):",
            json_output={"parent_id": task_id},
        )

        task_ids: list[str] = []
        while True:
            console.print("  [dim]>[/dim] ", end="")
            line = sys.stdin.readline()
            if not line or not line.strip():
                break
            child_id = add_subtask(config, task_id=task_id, title=line.strip())
            task_ids.append(child_id)
            console.print(f"  [green]task [blue]{child_id}[/blue] added[/green]")

        if task_ids:
            console.print(
                f"[green]Done:[/green] {len(task_ids)} task(s) added"
                f" to [blue]{task_id}[/blue]",
                json_output={"task_id": task_ids},
            )
        else:
            console.print(
                "[yellow]No tasks added.[/yellow]",
                json_output={"task_id": []},
            )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
