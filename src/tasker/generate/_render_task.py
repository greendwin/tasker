__all__ = ["render_task", "render_task_file"]

from pathlib import Path

from jinja2 import Environment, PackageLoader

from tasker.task import Task

_jinja = Environment(
    loader=PackageLoader("tasker", "templates"),
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_task(task: Task) -> str:
    return _jinja.get_template("task.md.j2").render(
        title=task.title,
        description=task.description,
        status=task.status.value,
    )


def render_task_file(path: Path, task: Task) -> None:
    path.write_text(render_task(task))
