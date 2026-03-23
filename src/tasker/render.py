from pathlib import Path

from jinja2 import Environment, PackageLoader

from .base_types import EXTENDED_TASK_FILENAME, BasicTask, ExtendedTask, TaskStatus

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


def render_task(task: BasicTask | ExtendedTask) -> str:
    return _jinja.get_template("task.md.j2").render(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status.value,
        subtasks=task.subtasks,
    )


def task_file_path(root: Path, task: BasicTask | ExtendedTask) -> Path:
    if task.parent is not None:
        # need to build nested path from root
        raise NotImplementedError("nested tasks are not supported yet")

    if isinstance(task, BasicTask):
        return root / f"{task.id}-{task.slug}.md"
    return root / f"{task.id}-{task.slug}" / EXTENDED_TASK_FILENAME


def write_task_file(
    root: Path, task: BasicTask | ExtendedTask, *, content: str
) -> None:
    path = task_file_path(root, task)
    path.parent.mkdir(exist_ok=True)
    path.write_text(content)
