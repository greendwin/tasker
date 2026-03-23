import re
from pathlib import Path
from typing import NamedTuple

from .base_types import (
    EXTENDED_TASK_FILENAME,
    AnyTask,
    BasicTask,
    ExtendedTask,
    InlineTask,
    TaskStatus,
    build_task_ref,
)
from .exceptions import TaskValidateError

# ID: s<digits> or s<digits>t<digits> (t appears once; each level adds two digits)
_SUBTASK_RE = re.compile(r"^- \[(.)\] (s\d+t(?:\d{2})+): (.+)$")
_CHECKBOX_STATUS = {
    " ": TaskStatus.PENDING,
    "~": TaskStatus.IN_PROGRESS,
    "x": TaskStatus.DONE,
}


class ParsedRef(NamedTuple):
    value: str  # original value "id-slug or id"
    task_id: str
    slug: str | None
    parent_id: str
    root_id: str


def parse_task_ref(task_ref: str) -> ParsedRef:
    # strip optional slug from input like "s01t01-define-task-forms"
    m = re.match(r"^(s\d+(?:t(?:\d{2})+)?)", task_ref)
    if not m:
        raise TaskValidateError(f"Invalid task ref: {task_ref!r}", task_ref=task_ref)
    task_id = m.group(1)
    rest = task_ref[m.end() :]
    slug = rest[1:] if rest.startswith("-") else None

    if "t" not in task_id:
        root_id = task_id
        parent_id = task_id
    else:
        t_pos = task_id.index("t")
        root_id = task_id[:t_pos]
        digits_after_t = task_id[t_pos + 1 :]
        parent_id = task_id[:t_pos] if len(digits_after_t) == 2 else task_id[:-2]

    return ParsedRef(
        value=task_ref,
        task_id=task_id,
        slug=slug,
        parent_id=parent_id,
        root_id=root_id,
    )


class TaskDetectResult(NamedTuple):
    task_ref: str
    task_id: str
    slug: str
    extended: bool
    content_path: Path


def detect_task_type(task_path: Path) -> TaskDetectResult:
    if task_path.is_dir():
        extended = True
        task_ref = task_path.name
        content_path = task_path / EXTENDED_TASK_FILENAME
    else:
        extended = False
        task_ref = task_path.stem
        content_path = task_path

    ref = parse_task_ref(task_ref)
    if ref.slug is None:
        raise TaskValidateError(
            f"Invalid task {task_path!r} with missing slug", task_ref=task_ref
        )

    return TaskDetectResult(
        task_ref=ref.value,
        task_id=ref.task_id,
        slug=ref.slug,
        extended=extended,
        content_path=content_path,
    )


def parse_task(
    content: str, *, task_id: str, slug: str, extended: bool
) -> BasicTask | ExtendedTask:
    parsed = _parse_content(content, task_ref=build_task_ref(task_id, slug))

    task_cls = ExtendedTask if extended else BasicTask
    return task_cls(
        id=parsed.id,
        slug=slug,
        title=parsed.title,
        description=parsed.description,
        status=parsed.status,
        subtasks=parsed.subtasks,
    )


def parse_task_file(path: Path) -> BasicTask | ExtendedTask:
    tt = detect_task_type(path)
    content = tt.content_path.read_text(encoding="utf-8")
    return parse_task(content, task_id=tt.task_id, slug=tt.slug, extended=tt.extended)


class _ParsedContent(NamedTuple):
    id: str
    title: str
    description: str | None
    status: TaskStatus
    subtasks: list[AnyTask]


def _parse_content(content: str, *, task_ref: str) -> _ParsedContent:
    lines = content.splitlines()

    if not lines or lines[0] != "---":
        raise TaskValidateError(
            "Missing front-matter: file must start with '---'", task_ref=task_ref
        )

    try:
        fm_end = lines.index("---", 1)
    except ValueError:
        raise TaskValidateError(
            "Unclosed front-matter: missing closing '---'", task_ref=task_ref
        )

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
        raise TaskValidateError("Missing title after front-matter", task_ref=task_ref)

    if not body[0].startswith("# "):
        raise TaskValidateError("Title must be a '# Heading' line", task_ref=task_ref)

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
                    )
                )

    return _ParsedContent(
        id=id_val,
        title=title,
        description=description,
        status=status,
        subtasks=subtasks,
    )
