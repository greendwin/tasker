from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

from tasker.base_types import Task, is_root_task_id
from tasker.exceptions import TaskValidateError
from tasker.parse import parse_task_ref

from ._utils import generate_slug, get_status_from_subtasks, has_file_subtasks

if TYPE_CHECKING:
    from ._task_repo import TaskRepo


class TaskRename(NamedTuple):
    old_id: str
    new_id: str


def move_task_impl(
    repo: TaskRepo,
    task: Task,
    *,
    new_parent: Task | None,
) -> list[TaskRename]:
    if new_parent is None:
        if is_root_task_id(task.id):
            # already a root task
            return []
    else:
        if new_parent.id == task.id:
            raise TaskValidateError(
                f"Cannot move {task.id!r} under itself.",
                task_ref=task.id,
            )

        ref = parse_task_ref(task.id)
        if ref.parent_id == new_parent.id:
            # already under target parent
            return []

        if _is_descendant_of(new_parent.id, task.id):
            raise TaskValidateError(
                f"Cannot move {task.id!r} under its descendant {new_parent.id!r}.",
                task_ref=task.id,
            )

    # --- collect old file paths before any mutation ---
    old_paths = _collect_task_paths(repo, task)

    # --- detach from current parent ---
    _detach_task(repo, task)

    # --- compute new ID and re-ID subtree ---
    new_id = repo._next_child_id(new_parent)
    renames = _reassign_ids(repo, task, new_id)

    # ensure task is file-backed (root tasks and subtasks under a parent
    # that will be flushed both need a slug)
    if task.slug is None:
        task.slug = generate_slug(task.title)

    # --- attach to new location ---
    if new_parent is None:
        repo._root_tasks[task.id] = task
    else:
        if new_parent.is_inline:
            new_parent.slug = generate_slug(new_parent.title)
        new_parent.subtasks.append(task)
        repo._update_parents_status(task)

    # --- persist ---
    repo.flush_to_disk()

    # --- remove old files ---
    for path in old_paths:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.is_file():
            path.unlink()

    return renames


def _is_descendant_of(child_id: str, ancestor_id: str) -> bool:
    """True when *child_id* is a strict descendant of *ancestor_id*."""
    prefix = ancestor_id if "t" in ancestor_id else ancestor_id + "t"
    return child_id.startswith(prefix) and len(child_id) > len(ancestor_id)


def _collect_task_paths(repo: TaskRepo, task: Task) -> list[Path]:
    if task.is_inline:
        return []
    container = _get_container_path(repo, task.id)
    if task.extended:
        return [container / task.ref]
    return [container / f"{task.ref}.md"]


def _get_container_path(repo: TaskRepo, task_id: str) -> Path:
    if is_root_task_id(task_id):
        return repo.root
    ref = parse_task_ref(task_id)
    parent = repo._tasks[ref.parent_id]
    return _get_container_path(repo, ref.parent_id) / parent.ref


def _detach_task(repo: TaskRepo, task: Task) -> None:
    if is_root_task_id(task.id):
        del repo._root_tasks[task.id]
        return

    ref = parse_task_ref(task.id)
    parent = repo._tasks[ref.parent_id]
    parent.subtasks = [s for s in parent.subtasks if s.id != task.id]

    # refresh old parent + ancestors
    parent.status = get_status_from_subtasks(parent)
    parent.extended = parent.extended or has_file_subtasks(parent)
    cur_id = parent.id
    while not is_root_task_id(cur_id):
        ri = parse_task_ref(cur_id)
        ancestor = repo._tasks[ri.parent_id]
        ancestor.status = get_status_from_subtasks(ancestor)
        ancestor.extended = ancestor.extended or has_file_subtasks(ancestor)
        cur_id = ancestor.id


def _reassign_ids(repo: TaskRepo, task: Task, new_id: str) -> list[TaskRename]:
    renames: list[TaskRename] = []

    old_child_prefix = task.id if "t" in task.id else task.id + "t"
    new_child_prefix = new_id if "t" in new_id else new_id + "t"

    old_id = task.id
    repo._tasks.pop(old_id, None)
    repo._disk_state.pop(old_id, None)

    task.id = new_id
    repo._tasks[new_id] = task
    renames.append(TaskRename(old_id=old_id, new_id=new_id))

    for subtask in task.subtasks:
        old_child_id = subtask.id
        suffix = old_child_id[len(old_child_prefix) :]
        new_child_id = new_child_prefix + suffix
        renames.extend(_reassign_ids(repo, subtask, new_child_id))

    return renames
