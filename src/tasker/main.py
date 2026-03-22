import re
from pathlib import Path
from typing import Annotated, Optional

import typer
from typer_di import TyperDI

from tasker.task import Task, TaskStatus
from tasker.generate import render_task_file
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


@app.command("add")
def add_task(
    title: Annotated[str, typer.Argument(help="Task title.")],
    description: Annotated[
        Optional[str], typer.Option("--description", "-d", help="Task description.")
    ] = None,
    slug: Annotated[
        Optional[str], typer.Option("--slug", help="Override auto-derived slug.")
    ] = None,
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

    task = Task(
        id=story_id,
        slug=slug,
        title=title,
        description=description,
        status=TaskStatus.PENDING,
        subtasks=[],
        loaded=True,
        filename=filename,
    )
    render_task_file(root / f"{filename}.md", task)

    console.print(f"[green]task [blue]{filename}[/blue] created[/green]")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
