import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from typer_di import Depends, TyperDI

from tasker.base_types import BasicTask, ExtendedTask, TaskStatus, is_nonleaf_task
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

        if task.status == TaskStatus.IN_PROGRESS:
            # resave tasks in case of outdated statuses
            repo.flush_to_disk()

            console.print(
                f"[green]Task [blue]{task.ref}[/blue] was already started[/green]",
                json_output={"task_ref": task.ref},
            )
            return

        if not console.json_output and is_nonleaf_task(task):
            _report_starting_nonleaf_task(task)
            raise typer.Exit(1)

        prev_status = task.status
        repo.start_task(task)
        repo.flush_to_disk()

        if prev_status == TaskStatus.DONE:
            action = "restarted"
        else:
            action = "started"

        console.print(
            f"[green]Task [blue]{task.ref}[/blue] {action}[/green]",
            json_output={"task_ref": task.ref},
        )


def _report_starting_nonleaf_task(task: BasicTask | ExtendedTask) -> None:
    console.print(
        f"[yellow]Task [blue]{task.ref}[/blue] has subtasks"
        " — its status is managed automatically.[/yellow]"
    )

    if task.status == TaskStatus.IN_PROGRESS:
        in_progress = [t for t in task.subtasks if t.status == TaskStatus.IN_PROGRESS]
        console.print("\nIn-progress subtasks:")
        for t in in_progress:
            console.print(f"  [blue]{t.id}[/blue]: {t.title}")
        return

    pending = [t for t in task.subtasks if t.status == TaskStatus.PENDING]
    console.print("Start one of its pending subtasks instead.")
    if not pending:
        console.print("\n[dim]No pending subtasks.[/dim]")
        return

    console.print("\nPending subtasks:")
    for t in pending:
        console.print(f"  [blue]{t.id}[/blue]: {t.title}")


@app.command("cancel")
def cmd_cancel_task(
    *,
    task_ref: Annotated[str, typer.Argument(help="Task ID to cancel.")],
    force: Annotated[
        bool,
        typer.Option("--force", help="Force cancel all open subtasks."),
    ] = False,
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    with console.catching_output():
        task = repo.resolve_ref(task_ref)

        if task.status == TaskStatus.CANCELLED:
            # resave tasks in case of outdated statuses
            repo.flush_to_disk()

            console.print(
                f"[green]Task [blue]{task.ref}[/blue] was already cancelled[/green]",
                json_output={"task_ref": task.ref},
            )
            return

        if not force and not console.json_output and is_nonleaf_task(task):
            _report_cancelling_nonleaf_task(task)
            raise typer.Exit(1)

        forced = repo.cancel_task(task, force=force)
        repo.flush_to_disk()

        if forced:
            console.print(
                "[yellow]Forcibly cancelled subtasks:[/yellow]",
                json_output={
                    "forced_task_ids": [t.id for t in forced],
                },
            )
            for t in forced:
                console.print(f"  [blue]{t.id}[/blue]: {t.title}")

        console.print(
            f"[green]Task [blue]{task.ref}[/blue] cancelled[/green]",
            json_output={"task_ref": task.ref},
        )


def _report_cancelling_nonleaf_task(
    task: BasicTask | ExtendedTask,
) -> None:
    open_tasks = [t for t in task.subtasks if not t.is_closed]

    console.print(
        f"[yellow]Task [blue]{task.ref}[/blue] has subtasks"
        " — its status is managed automatically.[/yellow]"
    )

    if not open_tasks:
        console.print("All subtasks are already closed.")
        return

    console.print("Cancel its open subtasks first, or use [bold]--force[/bold].")
    console.print("\nOpen subtasks:")
    for t in open_tasks:
        console.print(f"  [blue]{t.id}[/blue]: {t.title}")


@app.command("done")
def cmd_done_task(
    *,
    task_ref: Annotated[str, typer.Argument(help="Task ID to mark done.")],
    force: Annotated[
        bool,
        typer.Option("--force", help="Force close all open subtasks."),
    ] = False,
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    with console.catching_output():
        task = repo.resolve_ref(task_ref)

        if task.status == TaskStatus.DONE:
            # resave tasks in case of outdated statuses
            repo.flush_to_disk()

            console.print(
                f"[green]Task [blue]{task.ref}[/blue] was already finished[/green]",
                json_output={"task_ref": task.ref},
            )
            return

        if not force and not console.json_output and is_nonleaf_task(task):
            _report_finishing_nonleaf_task(task)
            raise typer.Exit(1)

        forced = repo.finish_task(task, force=force)
        repo.flush_to_disk()

        if forced:
            console.print(
                "[yellow]Forcibly closed subtasks:[/yellow]",
                json_output={
                    "forced_task_ids": [t.id for t in forced],
                },
            )
            for t in forced:
                console.print(f"  [blue]{t.id}[/blue]: {t.title}")

        console.print(
            f"[green]Task [blue]{task.ref}[/blue] finished[/green]",
            json_output={"task_ref": task.ref},
        )


def _report_finishing_nonleaf_task(task: BasicTask | ExtendedTask) -> None:
    open_tasks = [t for t in task.subtasks if not t.is_closed]

    console.print(
        f"[yellow]Task [blue]{task.ref}[/blue] has subtasks"
        " — its status is managed automatically.[/yellow]"
    )

    if not open_tasks:
        console.print("All subtasks are already closed.")
        return

    console.print("Finish its open subtasks first, or use [bold]--force[/bold].")

    console.print("\nOpen subtasks:")
    for t in open_tasks:
        console.print(f"  [blue]{t.id}[/blue]: {t.title}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
