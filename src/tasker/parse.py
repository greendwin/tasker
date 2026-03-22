import re
from pathlib import Path
from typing import NamedTuple

from .exceptions import TaskValidateError
from .base_types import (
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
    id: str
    title: str
    description: str | None
    status: TaskStatus
    subtasks: list[AnyTask]


def _parse_content(content: str) -> _ParsedContent:
    lines = content.splitlines()

    if not lines or lines[0] != "---":
        raise TaskValidateError("Missing front-matter: file must start with '---'")

    try:
        fm_end = lines.index("---", 1)
    except ValueError:
        raise TaskValidateError("Unclosed front-matter: missing closing '---'")

    id_val = ""
    status = TaskStatus.PENDING
    for line in lines[1:fm_end]:
        if line.startswith("id:"):
            id_val = line.split(":", 1)[1].strip()
        elif line.startswith("status:"):
            status = TaskStatus(line.split(":", 1)[1].strip())

    # Body: everything after the closing ---
    body = lines[fm_end + 1 :]
    while body and not body[0].strip():
        body.pop(0)

    if not body:
        raise TaskValidateError("Missing title after front-matter")

    if not body[0].startswith("# "):
        raise TaskValidateError("Title must be a '# Heading' line")
    title = body[0][2:]

    # Find ## Subtasks section in body[1:]
    subtasks_idx: int | None = None
    for i, line in enumerate(body[1:], 1):
        if line == "## Subtasks":
            subtasks_idx = i
            break

    desc_end = subtasks_idx if subtasks_idx is not None else len(body)
    desc_lines = body[1:desc_end]
    while desc_lines and not desc_lines[0].strip():
        desc_lines.pop(0)
    while desc_lines and not desc_lines[-1].strip():
        desc_lines.pop()
    description = "\n".join(desc_lines) or None

    subtasks: list[AnyTask] = []
    if subtasks_idx is not None:
        for line in body[subtasks_idx + 1 :]:
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
        id=id_val,
        title=title,
        description=description,
        status=status,
        subtasks=subtasks,
    )


def parse_task(task: Path) -> BasicTask | ExtendedTask:
    detailed = task.is_dir()
    content_path = task / EXTENDED_TASK_FILENAME if detailed else task
    stem = task.name if detailed else task.stem

    m = _STEM_RE.match(stem)
    if not m:
        raise TaskValidateError(f"Invalid task filename: {stem!r}", task_ref=str(task))
    slug = m.group(2)

    try:
        parsed = _parse_content(content_path.read_text())
    except TaskValidateError as ex:
        ex.task_ref = str(task)
        raise

    task_cls = ExtendedTask if detailed else BasicTask
    return task_cls(
        parent=None,
        id=parsed.id,
        slug=slug,
        title=parsed.title,
        description=parsed.description,
        status=parsed.status,
        subtasks=parsed.subtasks,
    )
