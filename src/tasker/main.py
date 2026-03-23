import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from typer_di import Depends, TyperDI

from tasker.base_types import BasicTask, ExtendedTask, InlineTask, TaskStatus
from tasker.task_repo import TaskRepo
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


def get_task_repo() -> TaskRepo:
    # TODO: this should be `.tasker` or configured using it
    planning = Path("planning")
    planning.mkdir(exist_ok=True)
    return TaskRepo(planning)


@app.command("new")
def cmd_new_task(
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
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    with console.catching_output():
        task = repo.create_root_task(
            title=title, description=details, slug=slug, extended=extended
        )
        repo.flush_to_disk()

        console.print(
            f"[green]Task [blue]{task.ref}[/blue] created[/green]",
            json_output={"task_ref": task.ref},
        )


@app.command("add")
def cmd_add_task(
    *,
    parent_ref: Annotated[str, typer.Argument(help="Parent task ID.")],
    title: Annotated[str, typer.Argument(help="Subtask title.")],
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    with console.catching_output():
        parent = repo.resolve_ref(parent_ref)
        child = repo.add_subtask(parent, title=title)
        repo.flush_to_disk()

        console.print(
            f"[green]Task [blue]{child.ref}[/blue]"
            f" added to [blue]{parent.ref}[/blue][/green]",
            json_output={"task_ref": child.ref},
        )


@app.command("add-many")
def cmd_add_many_tasks(
    *,
    parent_ref: Annotated[str, typer.Argument(help="Parent task ID.")],
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    with console.catching_output():
        parent = repo.resolve_ref(parent_ref)
        console.print(
            f"[cyan]Adding tasks to [blue]{parent.ref}[/blue][/cyan]"
            " (empty line to finish):",
            json_output={"parent_ref": parent_ref},
        )

        task_refs: list[str] = []
        while True:
            console.print("  [dim]>[/dim] ", end="")
            line = sys.stdin.readline()
            if not line or not line.strip():
                break
            child = repo.add_subtask(parent, title=line.strip())
            repo.flush_to_disk()
            task_refs.append(child.ref)
            console.print(f"  [green]task [blue]{child.ref}[/blue] added[/green]")

        if not task_refs:
            console.print(
                "[yellow]No tasks added.[/yellow]",
                json_output={"task_refs": []},
            )
            return

        console.print(
            f"[green]Done:[/green] {len(task_refs)} task(s) added"
            f" to [blue]{parent.id}[/blue]",
            json_output={"task_refs": task_refs},
        )


@app.command("start")
def cmd_start_task(
    *,
    task_ref: Annotated[str, typer.Argument(help="Task ID to mark in-progress.")],
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    with console.catching_output():
        task = repo.resolve_ref(task_ref)

        if (
            not console.json_output
            and not isinstance(task, InlineTask)
            and task.subtasks
        ):
            # on `--json-output` - write human friendly message, otherwise raise
            _report_starting_nonleaf_task(task)
            raise typer.Exit(1)

        prev_status = task.status
        repo.start_task(task)
        repo.flush_to_disk()

        if prev_status == TaskStatus.DONE:
            action = "restarted"
        elif prev_status == TaskStatus.IN_PROGRESS:
            action = "was already started"
        else:
            action = "started"

        console.print(
            f"[green]Task [blue]{task.ref}[/blue] {action}[/green]",
            json_output={"task_id": task.id},
        )


def _report_starting_nonleaf_task(task: BasicTask | ExtendedTask) -> None:
    pending = [t for t in task.subtasks if t.status == TaskStatus.PENDING]

    console.print(
        f"[yellow]Task [blue]{task.ref}[/blue] has subtasks"
        " — its status is managed automatically.[/yellow]"
    )
    console.print("Start one of its pending subtasks instead.")

    if pending:
        console.print("\nPending subtasks:")
        for t in pending:
            console.print(f"  [blue]{t.id}[/blue]: {t.title}")
    else:
        console.print("\n[dim]No pending subtasks.[/dim]")


@app.command("done")
def cmd_done_task(
    *,
    task_ref: Annotated[str, typer.Argument(help="Task ID to mark done.")],
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    with console.catching_output():
        task = repo.resolve_ref(task_ref)

        if (
            not console.json_output
            and not isinstance(task, InlineTask)
            and task.subtasks
        ):
            _report_finishing_nonleaf_task(task)
            raise typer.Exit(1)

        prev_status = task.status
        repo.finish_task(task)
        repo.flush_to_disk()

        if prev_status == TaskStatus.DONE:
            action = "was already finished"
        else:
            action = "finished"

        console.print(
            f"[green]Task [blue]{task.ref}[/blue] {action}[/green]",
            json_output={"task_id": task.id},
        )


def _report_finishing_nonleaf_task(task: BasicTask | ExtendedTask) -> None:
    open_tasks = [t for t in task.subtasks if t.status != TaskStatus.DONE]
    assert len(open_tasks) > 0

    console.print(
        f"[yellow]Task [blue]{task.ref}[/blue] has subtasks"
        " — its status is managed automatically.[/yellow]"
    )
    console.print("Finish its open subtasks first.")

    console.print("\nOpen subtasks:")
    for t in open_tasks:
        console.print(f"  [blue]{t.id}[/blue]: {t.title}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
