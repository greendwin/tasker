__all__ = ["parse_task"]

import re
from pathlib import Path

from ._base_type import Task, TaskStatus

_STEM_RE = re.compile(r"^(s\d+(?:t\d+)?)-(.+)$")


def _parse_content(content: str) -> tuple[str, str | None, TaskStatus]:
    lines = content.splitlines()
    title = lines[0]

    props_idx = lines.index("## Props")

    desc_lines = lines[2:props_idx]
    while desc_lines and not desc_lines[0].strip():
        desc_lines.pop(0)
    while desc_lines and not desc_lines[-1].strip():
        desc_lines.pop()
    description = "\n".join(desc_lines) or None

    status = TaskStatus.PENDING
    for line in lines[props_idx + 1 :]:
        if line.startswith("Status:"):
            status = TaskStatus(line.split(":", 1)[1].strip())
            break

    return title, description, status


def parse_task(task: Path) -> Task:
    detailed = task.is_dir()
    content_path = task / "README.md" if detailed else task
    stem = task.name if detailed else task.stem

    m = _STEM_RE.match(stem)
    if not m:
        raise ValueError(f"Invalid task filename: {stem!r}")
    task_id, slug = m.group(1), m.group(2)

    title, description, status = _parse_content(content_path.read_text())

    return Task(
        id=task_id,
        slug=slug,
        title=title,
        description=description,
        status=status,
        subtasks=[],
        detailed=detailed,
        loaded=True,
        filename=stem,
    )
