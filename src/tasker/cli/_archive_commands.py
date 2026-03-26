from typing import Annotated

import typer
from typer_di import Depends

from tasker.base_types import Task, is_root_task_id
from tasker.task_repo import TaskRepo
from tasker.utils import JsonAppend, console

from ._common import app, get_task_repo, resolve_ref


@app.command("archive", help="Archive a completed root task.")
def cmd_archive_task(
    *,
    task_ref: Annotated[str, typer.Argument(help="Root task ID to archive.")],
    force: Annotated[
        bool,
        typer.Option("--force", help="Cancel open subtasks before archiving."),
    ] = False,
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    with console.catching_output():
        task = resolve_ref(repo, task_ref)

        if not console.json_output and not is_root_task_id(task.id):
            _report_not_root_task(task)
            raise typer.Exit(1)

        if not force and not console.json_output and not task.is_closed:
            _report_open_task(task)
            raise typer.Exit(1)

        forced = repo.archive_task(task, force=force)

        if forced:
            console.print("[yellow]Forcibly cancelled subtasks:[/yellow]")
            for t in forced:
                console.print(
                    f"  [blue]{t.id}[/blue]: {t.title}",
                    json_output={"forced_task_ids": JsonAppend(t.id)},
                )

        console.print(
            f"[green]Task [blue]{task.ref}[/blue] archived[/green]",
            json_output={"task_ref": task.ref},
        )


@app.command("unarchive", help="Restore an archived root task.")
def cmd_unarchive_task(
    *,
    task_ref: Annotated[str, typer.Argument(help="Root task ID to unarchive.")],
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    with console.catching_output():
        ref_name = repo.unarchive_task(task_ref)

        console.print(
            f"[green]Task [blue]{ref_name}[/blue] unarchived[/green]",
            json_output={"task_ref": ref_name},
        )


def _report_not_root_task(task: Task) -> None:
    console.print(
        f"[yellow]Only root tasks can be archived —"
        f" [blue]{task.ref}[/blue] is a subtask.[/yellow]"
    )


def _report_open_task(task: Task) -> None:
    console.print(f"[yellow]Task [blue]{task.ref}[/blue] is not closed.[/yellow]")

    open_tasks = [t for t in task.subtasks if not t.is_closed]
    if open_tasks:
        console.print("Close its open subtasks first, or use [bold]--force[/bold].")
        console.print("\nOpen subtasks:")
        for t in open_tasks:
            console.print(f"  [blue]{t.id}[/blue]: {t.title}")
    else:
        console.print("Use [bold]--force[/bold] to cancel and archive.")
