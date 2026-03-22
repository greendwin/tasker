import re
from pathlib import Path
from typing import NamedTuple

from ._base_types import EXTENDED_TASK_FILENAME, BasicTask, ExtendedTask, TaskStatus

# ID: s<digits> or s<digits>t<digits> (t appears once; each nesting level adds two digits)
_STEM_RE = re.compile(r"^(s\d+(?:t(?:\d{2})+)?)-(.+)$")


class _ParsedContent(NamedTuple):
    title: str
    description: str | None
    status: TaskStatus


def _parse_content(content: str) -> _ParsedContent:
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

    return _ParsedContent(title=title, description=description, status=status)


def parse_task(task: Path) -> BasicTask | ExtendedTask:
    detailed = task.is_dir()
    content_path = task / EXTENDED_TASK_FILENAME if detailed else task
    stem = task.name if detailed else task.stem

    m = _STEM_RE.match(stem)
    if not m:
        raise ValueError(f"Invalid task filename: {stem!r}")
    task_id, slug = m.group(1), m.group(2)

    parsed = _parse_content(content_path.read_text())

    task_cls = ExtendedTask if detailed else BasicTask
    return task_cls(
        parent=None,
        id=task_id,
        slug=slug,
        title=parsed.title,
        description=parsed.description,
        status=parsed.status,
        subtasks=[],
    )
