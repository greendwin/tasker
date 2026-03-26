import re
from pathlib import Path

from tasker.base_types import Task, TaskStatus


def generate_slug(title: str) -> str:
    words = re.sub(r"[^a-z0-9\s]", "", title.lower()).split()[:5]
    return "-".join(words)


def find_next_root_task_id(root: Path, archive_root: Path) -> str:
    existing = _scan_root_task_nums(root) + _scan_root_task_nums(archive_root)
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
    child_prefix = parent.id if "t" in parent.id else parent.id + "t"
    existing_nums = [
        int(t.id[len(child_prefix) :])
        for t in parent.subtasks
        if t.id.startswith(child_prefix) and len(t.id) == len(child_prefix) + 2
    ]
    return f"{child_prefix}{max(existing_nums, default=0) + 1:02d}"


def get_status_from_subtasks(task: Task) -> TaskStatus:
    if not task.subtasks:
        # no subtasks -- kepp status same
        return task.status

    if all(t.is_closed for t in task.subtasks):
        if all(t.status == TaskStatus.CANCELLED for t in task.subtasks):
            return TaskStatus.CANCELLED
        return TaskStatus.DONE
    if any(t.status == TaskStatus.IN_PROGRESS for t in task.subtasks):
        return TaskStatus.IN_PROGRESS
    return TaskStatus.PENDING


def invalidate_task_flags(root: Task) -> None:
    if root.is_inline:
        return

    for child in root.subtasks:
        invalidate_task_flags(child)

    # update root itself
    root.status = get_status_from_subtasks(root)
    root.extended = root.extended or has_file_subtasks(root)


def has_file_subtasks(task: Task) -> bool:
    return any(not s.is_inline for s in task.subtasks)
