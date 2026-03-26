from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from tasker.base_types import Task, TaskStatus, is_root_task_id
from tasker.parse import make_child_ref, parse_task_ref

if TYPE_CHECKING:
    from ._task_loader import TaskLoader


def generate_slug(title: str) -> str:
    words = re.sub(r"[^a-z0-9\s]", "", title.lower()).split()[:5]
    return "-".join(words)


def find_next_root_task_id(loader: TaskLoader) -> str:
    existing = _scan_root_task_nums(loader.root) + _scan_root_task_nums(
        loader.archive_root
    )
    return f"s{max(existing, default=0) + 1:02d}"


def _scan_root_task_nums(directory: Path) -> list[int]:
    if not directory.is_dir():
        return []
    return [
        int(m.group(1))
        for p in directory.iterdir()
        if (m := re.match(r"^s(\d+)", p.name))
    ]


def get_next_subtask_id(parent: Task) -> str:
    child_prefix = make_child_ref(parent.id, "")
    existing_nums = [
        int(t.id[len(child_prefix) :])
        for t in parent.subtasks
        if t.id.startswith(child_prefix) and len(t.id) == len(child_prefix) + 2
    ]
    return f"{child_prefix}{max(existing_nums, default=0) + 1:02d}"


def get_status_from_subtasks(task: Task) -> TaskStatus:
    if not task.subtasks:
        # no subtasks -- keep status unchanged
        return task.status

    if all(t.is_closed for t in task.subtasks):
        if all(t.status == TaskStatus.CANCELLED for t in task.subtasks):
            return TaskStatus.CANCELLED
        return TaskStatus.DONE
    if any(t.status == TaskStatus.IN_PROGRESS for t in task.subtasks):
        return TaskStatus.IN_PROGRESS
    return TaskStatus.PENDING


def has_file_subtasks(task: Task) -> bool:
    return any(not s.is_inline for s in task.subtasks)


def update_parents_status(
    task: Task, *, loader: TaskLoader, update_itself: bool = False
) -> None:
    if update_itself:
        task.status = get_status_from_subtasks(task)
        task.extended = has_file_subtasks(task)

    cur_id = task.id
    while not is_root_task_id(cur_id):
        ri = parse_task_ref(cur_id)
        parent = loader.resolve_ref(ri.parent_id)

        assert not parent.is_inline
        parent.status = get_status_from_subtasks(parent)
        parent.extended = has_file_subtasks(parent)
        cur_id = parent.id


def try_downgrade_to_inline(task: Task) -> None:
    if task.is_inline or is_root_task_id(task.id):
        return

    if task.description is not None or task.extra_sections is not None:
        return

    if task.subtasks:
        return
    
    task.slug = None
    task.extended = False


def upgrade_to_filebased(task: Task, *, loader: TaskLoader) -> None:
    if not task.is_inline:
        # already file-based
        return

    task.slug = generate_slug(task.title)
    update_parents_status(task, loader=loader)
