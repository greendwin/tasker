from pathlib import Path

from jinja2 import Environment, PackageLoader

from ._base_types import EXTENDED_TASK_FILENAME, BasicTask, FileTask, TaskStatus

_CHECKBOX = {
    TaskStatus.PENDING: " ",
    TaskStatus.IN_PROGRESS: "~",
    TaskStatus.DONE: "x",
}

_jinja = Environment(
    loader=PackageLoader("tasker", "templates"),
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)


def _to_checkbox(status: TaskStatus) -> str:
    return _CHECKBOX[status]


_jinja.filters["checkbox"] = _to_checkbox


def render_task(task: FileTask) -> str:
    return _jinja.get_template("task.md.j2").render(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status.value,
        subtasks=task.subtasks,
    )


def render_task_file(root: Path, task: FileTask) -> None:
    if task.parent is not None:
        raise NotImplementedError("nested tasks are not supported yet")

    if isinstance(task, BasicTask):
        path = root / f"{task.id}-{task.slug}.md"
    else:
        path = root / f"{task.id}-{task.slug}" / EXTENDED_TASK_FILENAME

    path.parent.mkdir(exist_ok=True)
    path.write_text(render_task(task))
