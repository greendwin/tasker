from typing import Annotated, Optional

import typer
from typer_di import Depends

from tasker.base_types import Task, is_root_task_id
from tasker.exceptions import TaskValidateError
from tasker.repo import TaskRepo
from tasker.utils import JsonAppend, console

from ._common import app, get_task_repo, resolve_ref, save_recent_task


@app.command("arch", hidden=True)
@app.command("archive", help="Archive a completed root task.")
def cmd_archive_task(
    *,
    task_refs: Annotated[list[str], typer.Argument(help="Root task ID(s) to archive.")],
    force: Annotated[
        bool,
        typer.Option("--force", help="Cancel open subtasks before archiving."),
    ] = False,
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    with console.catching_output():
        for task_ref in task_refs:
            task = resolve_ref(repo, task_ref)

            if not console.json_output and not is_root_task_id(task.id):
                _report_not_root_task(task)
                raise typer.Exit(1)

            if not force and not console.json_output and not task.is_closed:
                _report_open_task(task)
                raise typer.Exit(1)

            forced = repo.archive_root_task(task, force=force)

            if forced:
                console.print("[yellow]Forcibly cancelled subtasks:[/yellow]")
                for t in forced:
                    console.print(
                        f"  - [blue]{t.id}[/blue]: {t.title}",
                        json_output={"forced_task_ids": JsonAppend(t.id)},
                    )

            console.print(
                f"[green]Task [blue]{task.ref}[/blue] archived[/green]",
                json_output={"task_refs": JsonAppend(task.ref)},
            )


@app.command("unarch", hidden=True)
@app.command("unarchive", help="Restore an archived root task.")
def cmd_unarchive_task(
    *,
    task_refs: Annotated[
        list[str], typer.Argument(help="Root task ID(s) to unarchive.")
    ],
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    with console.catching_output():
        for task_ref in task_refs:
            ref = repo.unarchive_root_task(task_ref)
            save_recent_task(repo, ref.task_id)

            console.print(
                f"[green]Task [blue]{ref.task_ref}[/blue] unarchived[/green]",
                json_output={"task_refs": JsonAppend(ref.task_ref)},
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
            console.print(f"  - [blue]{t.id}[/blue]: {t.title}")
    else:
        console.print("Use [bold]--force[/bold] to cancel and archive.")


@app.command("move", help="Move a task under a new parent or to root level.")
def cmd_move_task(
    *,
    task_refs: Annotated[list[str], typer.Argument(help="Task ID(s) to move.")],
    parent_ref: Annotated[
        Optional[str],
        typer.Option("--parent", "-p", help="New parent task ID."),
    ] = None,
    root: Annotated[
        bool,
        typer.Option("--root", help="Move task to root level (make it a story)."),
    ] = False,
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    with console.catching_output():
        if parent_ref is not None and root:
            raise TaskValidateError(
                "Cannot specify both --parent and --root.",
                task_ref=task_refs[0] if task_refs else "",
            )

        if parent_ref is None and not root:
            raise TaskValidateError(
                "Specify --parent <ref> or --root.",
                task_ref=task_refs[0] if task_refs else "",
            )

        new_parent = (
            resolve_ref(repo, parent_ref, auto_unarchive=True)
            if parent_ref is not None
            else None
        )

        if new_parent is not None:
            console.print("", end="", json_output={"parent_ref": new_parent.ref})

        for k, task_ref in enumerate(task_refs):
            task = resolve_ref(repo, task_ref, auto_unarchive=True)
            renames = repo.move_task(task, new_parent=new_parent)

            # save regenerated id
            save_recent_task(repo, task.id)

            if k > 0:
                console.print("")

            if not renames:
                # idempotent — task is already at the requested location
                console.print(
                    f"[green]Task [blue]{task.ref}[/blue]"
                    " is already in the requested location[/green]",
                    json_output={"task_refs": JsonAppend(task.ref), "already": True},
                )
                continue

            if new_parent is None:
                console.print(
                    f"[green]Task [blue]{task.ref}[/blue] moved to root[/green]",
                    json_output={"task_refs": JsonAppend(task.ref)},
                )
            else:
                console.print(
                    f"[green]Task [blue]{task.ref}[/blue]"
                    f" moved under [blue]{new_parent.ref}[/blue][/green]",
                    json_output={"task_refs": JsonAppend(task.ref)},
                )

            console.print("[yellow]Renamed tasks:[/yellow]")
            for r in renames:
                console.print(
                    f"  [cyan]{r.old_id}[/cyan] → [blue]{r.new_id}[/blue]",
                    json_output={
                        "renames": JsonAppend({"old_id": r.old_id, "new_id": r.new_id})
                    },
                )
