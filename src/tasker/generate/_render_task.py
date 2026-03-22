__all__ = ["render_task", "render_task_file"]

from pathlib import Path
from typing import Optional

from jinja2 import Environment, PackageLoader

_jinja = Environment(
    loader=PackageLoader("tasker", "templates"),
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_task(
    title: str,
    description: Optional[str] = None,
    status: str = "pending",
) -> str:
    return _jinja.get_template("task.md.j2").render(
        title=title,
        description=description,
        status=status,
    )


def render_task_file(
    path: Path,
    title: str,
    description: Optional[str] = None,
    status: str = "pending",
) -> None:
    path.write_text(render_task(title, description, status))
