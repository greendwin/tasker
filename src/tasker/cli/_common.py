from pathlib import Path
from typing import Annotated

import typer
from typer_di import TyperDI

from tasker.base_types import Task
from tasker.exceptions import TaskArchivedError, TaskValidateError
from tasker.repo import TaskRepo
from tasker.utils import console

_RECENT_FILE = ".recent"
_GITIGNORE_FILE = ".gitignore"


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
    tasker_dir = Path("tasker")
    tasker_dir.mkdir(exist_ok=True)
    return TaskRepo(tasker_dir)


def resolve_ref(repo: TaskRepo, task_ref: str, *, save_recent: bool = False) -> Task:
    if task_ref == "q":
        recent_id = load_recent(repo)
        if recent_id is None:
            raise TaskValidateError("Recent task was not set yet", task_ref=task_ref)

        task_ref = recent_id

    try:
        task = repo.resolve_ref(task_ref)
    except TaskArchivedError as ex:
        if console.json_output:
            raise

        console.print(f"[yellow]Task [blue]{ex.task_ref}[/blue] is archived.[/yellow]")
        console.print("Unarchive it first before performing actions on it.")
        raise typer.Exit(1) from ex
    else:
        if save_recent and _is_direct_link(task_ref):
            save_recent_task(repo, task.id)
        return task


def _is_direct_link(task_ref: str) -> bool:
    return task_ref.startswith("s")


def save_recent_task(repo: TaskRepo, task_id: str) -> None:
    _ensure_gitignore(repo.root)
    (repo.root / _RECENT_FILE).write_text(task_id + "\n")


def load_recent(repo: TaskRepo) -> str | None:
    path = repo.root / _RECENT_FILE
    if not path.exists():
        return None
    text = path.read_text().strip()
    return text or None


def _ensure_gitignore(root: Path) -> None:
    gitignore = root / _GITIGNORE_FILE
    if not gitignore.exists():
        gitignore.write_text(_GITIGNORE_FILE + "\n" + _RECENT_FILE + "\n")
        return

    content = gitignore.read_text()
    if _RECENT_FILE in content.splitlines():
        return
    if not content.endswith("\n"):
        content += "\n"
    content += _RECENT_FILE + "\n"
    gitignore.write_text(content)
