from pathlib import Path

from jinja2 import Environment, PackageLoader

from .base_types import EXTENDED_TASK_FILENAME, Task, TaskStatus

_CHECKBOX = {
    TaskStatus.PENDING: " ",
    TaskStatus.IN_PROGRESS: "~",
    TaskStatus.DONE: "x",
    TaskStatus.CANCELLED: "x",
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


def render_task(task: Task) -> str:
    return _jinja.get_template("task.md.j2").render(
        id=task.id,
        title=task.title,
        description=task.description,
        extra_sections=task.extra_sections,
        status=task.status.value,
        subtasks=task.subtasks,
    )


def build_task_file_path(root: Path, task_ref: str, extended: bool) -> Path:
    if not extended:
        return root / f"{task_ref}.md"
    return root / task_ref / EXTENDED_TASK_FILENAME


def write_task_file(root: Path, task: Task, *, content: str) -> None:
    path = build_task_file_path(root, task.ref, task.extended)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
