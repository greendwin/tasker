import re
from dataclasses import dataclass
from pathlib import Path

from tasker.base_types import BasicTask, ExtendedTask, InlineTask, TaskStatus
from tasker.parse import parse_task
from tasker.render import render_task_file

from ._story_utils import find_task_file
from .exceptions import TaskerError


@dataclass
class TaskerConfig:
    root_dir: Path


def create_new_story(
    config: TaskerConfig,
    *,
    title: str,
    description: str | None,
    slug: str | None,
    extended: bool,
) -> str:
    root = config.root_dir
    title = title[:1].upper() + title[1:]

    existing = [
        int(m.group(1)) for p in root.iterdir() if (m := re.match(r"^s(\d+)", p.name))
    ]
    next_n = max(existing, default=0) + 1

    if slug is None:
        words = re.sub(r"[^a-z0-9\s]", "", title.lower()).split()[:5]
        slug = "-".join(words)

    story_id = f"s{next_n:02d}"
    filename = f"{story_id}-{slug}"

    task_type = ExtendedTask if extended else BasicTask

    task = task_type(
        parent=None,
        id=story_id,
        slug=slug,
        title=title,
        description=description,
        status=TaskStatus.PENDING,
        subtasks=[],
    )

    render_task_file(root, task)

    return filename


def ref_to_task_id(reference: str) -> str:
    # strip optional slug from input like "s01t01-define-task-forms"
    m = re.match(r"^(s\d+(?:t(?:\d{2})+)?)", reference)
    if not m:
        raise TaskerError(f"Invalid task ID: {reference!r}")
    task_id = m.group(1)
    return task_id


def add_subtask(config: TaskerConfig, *, task_id: str, title: str) -> str:
    root = config.root_dir
    title = title[:1].upper() + title[1:]

    task_path = find_task_file(root, task_id)

    parent = parse_task(task_path)

    # compute next child ID
    child_prefix = task_id if "t" in task_id else task_id + "t"
    existing_nums = [
        int(t.id[len(child_prefix) :])
        for t in parent.subtasks
        if t.id.startswith(child_prefix) and len(t.id) == len(child_prefix) + 2
    ]
    child_id = f"{child_prefix}{max(existing_nums, default=0) + 1:02d}"

    parent.subtasks.append(
        InlineTask(id=child_id, title=title, status=TaskStatus.PENDING, parent=None)
    )

    render_task_file(root, parent)
    return child_id
