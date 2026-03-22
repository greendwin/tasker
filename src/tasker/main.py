import re
from pathlib import Path
from typing import Annotated, Optional

import typer
from typer_di import TyperDI

from tasker.task import BasicTask, ExtendedTask, TaskStatus, render_task_file
from tasker.utils import console

app = TyperDI(
    name="tasker",
    help="File-based task tracker for git repos.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)


@app.callback()
def _callback() -> None:
    pass


def _get_root_dir() -> Path:
    planning = Path("planning")
    planning.mkdir(exist_ok=True)
    return planning


@app.command("new")
def new_task(
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
) -> None:
    root = _get_root_dir()

    existing = [
        int(m.group(1)) for p in root.iterdir() if (m := re.match(r"^s(\d+)", p.name))
    ]
    next_n = max(existing, default=0) + 1

    if slug is None:
        words = re.sub(r"[^a-z0-9\s]", "", title.lower()).split()[:5]
        slug = "-".join(words)

    story_id = f"s{next_n:02d}"
    filename = f"{story_id}-{slug}"

    task_type = ExtendedTask if extended else BasicTask

    task = task_type(
        parent=None,
        id=story_id,
        slug=slug,
        title=title,
        description=details or "",
        status=TaskStatus.PENDING,
        subtasks=[],
    )

    render_task_file(root, task)

    console.print(f"[green]task [blue]{filename}[/blue] created[/green]")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
