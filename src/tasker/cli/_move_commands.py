from typing import Annotated, Optional

import typer
from typer_di import Depends

from tasker.exceptions import TaskValidateError
from tasker.repo import TaskRepo
from tasker.utils import JsonAppend, console

from ._common import app, get_task_repo, resolve_ref


@app.command("move", help="Move a task under a new parent or to root level.")
def cmd_move_task(
    *,
    task_ref: Annotated[str, typer.Argument(help="Task ID to move.")],
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
                task_ref=task_ref,
            )

        if parent_ref is None and not root:
            raise TaskValidateError(
                "Specify --parent <ref> or --root.",
                task_ref=task_ref,
            )

        task = resolve_ref(repo, task_ref)
        new_parent = resolve_ref(repo, parent_ref) if parent_ref is not None else None
        renames = repo.move_task(task, new_parent=new_parent)

        if renames:
            console.print("[yellow]Renamed tasks:[/yellow]")
            for r in renames:
                console.print(
                    f"  {r.old_id} → {r.new_id}",
                    json_output={
                        "renames": JsonAppend({"old_id": r.old_id, "new_id": r.new_id})
                    },
                )

        if new_parent is not None:
            console.print(
                f"[green]Task [blue]{task.ref}[/blue]"
                f" moved under [blue]{new_parent.ref}[/blue][/green]",
                json_output={"task_ref": task.ref, "parent_ref": new_parent.ref},
            )
        else:
            console.print(
                f"[green]Task [blue]{task.ref}[/blue]" " moved to root[/green]",
                json_output={"task_ref": task.ref},
            )
