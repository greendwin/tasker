import re
from pathlib import Path
from typing import NamedTuple

from ._base_types import (
    EXTENDED_TASK_FILENAME,
    AnyTask,
    BasicTask,
    ExtendedTask,
    InlineTask,
    TaskStatus,
)

# ID: s<digits> or s<digits>t<digits> (t appears once; each level adds two digits)
_STEM_RE = re.compile(r"^(s\d+(?:t(?:\d{2})+)?)-(.+)$")
_SUBTASK_RE = re.compile(r"^- \[(.)\] (s\d+t(?:\d{2})+): (.+)$")
_CHECKBOX_STATUS = {
    " ": TaskStatus.PENDING,
    "~": TaskStatus.IN_PROGRESS,
    "x": TaskStatus.DONE,
}


class _ParsedContent(NamedTuple):
    title: str
    description: str | None
    status: TaskStatus
    subtasks: list[AnyTask]


def _parse_content(content: str) -> _ParsedContent:
    lines = content.splitlines()
    title = lines[0]

    section_idx: dict[str, int] = {}
    for i, line in enumerate(lines):
        if line.startswith("## "):
            section_idx[line[3:]] = i

    props_idx = section_idx["Props"]
    subtasks_idx = section_idx.get("Subtasks")

    desc_end = subtasks_idx if subtasks_idx is not None else props_idx
    desc_lines = lines[2:desc_end]
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

    subtasks: list[AnyTask] = []
    if subtasks_idx is not None:
        for line in lines[subtasks_idx + 1 : props_idx]:
            m = _SUBTASK_RE.match(line)
            if m:
                checkbox, task_id, task_title = m.group(1), m.group(2), m.group(3)
                subtasks.append(
                    InlineTask(
                        id=task_id,
                        title=task_title,
                        status=_CHECKBOX_STATUS.get(checkbox, TaskStatus.PENDING),
                        parent=None,
                    )
                )

    return _ParsedContent(
        title=title, description=description, status=status, subtasks=subtasks
    )


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
        subtasks=parsed.subtasks,
    )
