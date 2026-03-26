from dataclasses import dataclass
from pathlib import Path

from tasker.base_types import Task, TaskStatus
from tasker.exceptions import TaskArchivedError, TaskHasSubtasksError, TaskValidateError
from tasker.parse import ParsedSubtask, detect_task_type, parse_task, parse_task_ref
from tasker.render import build_task_file_path, render_task, write_task_file

from ._archive_task import archive_task_impl, unarchive_task_impl
from ._move_task import TaskRename, move_task_impl
from ._utils import (
    find_next_root_task_id,
    generate_slug,
    get_next_subtask_id,
    invalidate_task_flags,
    update_parents_status,
)

_ARCHIVE_DIR = "archive"


@dataclass
class _DiskState:
    content: str
    extended: bool


class TaskRepo:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.archive_root = root / _ARCHIVE_DIR
        self._root_tasks: dict[str, Task] = {}
        self._tasks: dict[str, Task] = {}
        self._disk_state: dict[str, _DiskState] = {}

    def resolve_ref(self, task_ref: str) -> Task:
        ti = parse_task_ref(task_ref)

        if ti.root_id not in self._root_tasks:
            self._load_root_task(ti.root_id)

        task = self._tasks.get(ti.task_id)
        if task is None:
            raise TaskValidateError(
                f"Cannot resolve task reference {task_ref!r}", task_ref=task_ref
            )

        return task

    def create_root_task(
        self,
        *,
        title: str,
        description: str | None,
        slug: str | None,
        extended: bool,
    ) -> Task:
        title = title[:1].upper() + title[1:]
        root_id = self._next_child_id(None)

        if slug is None:
            slug = generate_slug(title)

        task = Task(
            id=root_id,
            slug=slug,
            extended=extended,
            title=title,
            description=description,
        )

        self._root_tasks[root_id] = task
        self._tasks[root_id] = task
        self._disk_state[root_id] = _DiskState(content="", extended=extended)

        return task

    def add_subtask(
        self,
        parent: Task,
        *,
        title: str,
        description: str | None = None,
        slug: str | None = None,
    ) -> Task:
        title = title[:1].upper() + title[1:]

        if parent.is_inline:
            # upgrade inline task to basic (file-backed) form
            parent.slug = generate_slug(parent.title)

        child_id = self._next_child_id(parent)

        if description is not None and slug is None:
            # generate slug (i.e. with description task cannot be inline)
            slug = generate_slug(title)

        subtask = Task(
            id=child_id,
            slug=slug,
            title=title,
            description=description,
        )

        parent.subtasks.append(subtask)
        self._tasks[child_id] = subtask
        update_parents_status(subtask, repo=self)

        return subtask

    def _next_child_id(self, parent: Task | None) -> str:
        if parent is None:
            return find_next_root_task_id(self.root, self.archive_root)

        return get_next_subtask_id(parent)

    def start_task(self, task: Task) -> None:
        if not _is_leaf_task(task):
            raise TaskHasSubtasksError(task)

        task.status = TaskStatus.IN_PROGRESS
        update_parents_status(task, repo=self)

    def reset_task(self, task: Task) -> None:
        if not _is_leaf_task(task):
            raise TaskHasSubtasksError(task)

        task.status = TaskStatus.PENDING
        update_parents_status(task, repo=self)

    def cancel_task(self, task: Task, *, force: bool = False) -> list[Task] | None:
        if _is_leaf_task(task):
            task.status = TaskStatus.CANCELLED
            update_parents_status(task, repo=self)
            return None

        if not force:
            raise TaskHasSubtasksError(task)

        closed_tasks: list[Task] = []
        _close_recursive(task, TaskStatus.CANCELLED, closed_tasks)
        update_parents_status(task, repo=self)
        return closed_tasks[1:]  # don't include root task

    def finish_task(self, task: Task, *, force: bool = False) -> list[Task] | None:
        if _is_leaf_task(task):
            task.status = TaskStatus.DONE
            update_parents_status(task, repo=self)
            return None

        if not force:
            raise TaskHasSubtasksError(task)

        closed_tasks: list[Task] = []
        _close_recursive(task, TaskStatus.DONE, closed_tasks)
        update_parents_status(task, repo=self)
        return closed_tasks[1:]  # don't include root task

    def archive_task(self, task: Task, *, force: bool = False) -> list[Task] | None:
        return archive_task_impl(self, task, force=force)

    def unarchive_task(self, task_ref: str) -> str:
        return unarchive_task_impl(self, task_ref)

    def move_task(
        self,
        task: Task,
        *,
        new_parent: Task | None,
    ) -> list[TaskRename]:
        return move_task_impl(self, task, new_parent=new_parent)

    def flush_to_disk(self) -> None:
        for task in self._root_tasks.values():
            self._flush_task(self.root, task)

    def _flush_task(self, root: Path, task: Task) -> None:
        rendered = render_task(task)
        prev = self._disk_state.get(task.id)
        was_extended = prev.extended if prev else task.extended
        prev_content = prev.content if prev else ""
        upgraded = not was_extended and task.extended
        content_changed = rendered != prev_content

        if upgraded:
            # upgraded from basic to extended — remove old .md file
            old_path = root / f"{task.ref}.md"
            if old_path.exists():
                old_path.unlink()

        if content_changed or upgraded:
            write_task_file(root, task, content=rendered)
            self._disk_state[task.id] = _DiskState(
                content=rendered, extended=task.extended
            )

        # recursively flush file-backed subtasks
        if task.extended:
            subtask_root = root / task.ref
            for subtask in task.subtasks:
                if not subtask.is_inline:
                    self._flush_task(subtask_root, subtask)

    def _load_root_task(self, root_id: str) -> None:
        assert root_id not in self._root_tasks

        candidates = list(self.root.glob(f"{root_id}-*"))
        if not candidates:
            if any(self.archive_root.glob(f"{root_id}-*")):
                raise TaskArchivedError(root_id)
            raise TaskValidateError(f"Task {root_id!r} not found", task_ref=root_id)

        if len(candidates) > 1:
            names = ", ".join(p.name for p in candidates)
            raise TaskValidateError(
                f"Ambiguous task {root_id!r}: multiple files match: {names}",
                task_ref=root_id,
            )

        tt = detect_task_type(candidates[0])
        assert tt.task_id == root_id

        content = tt.content_path.read_text(encoding="utf-8")

        root, subtasks = parse_task(
            content,
            task_id=tt.task_id,
            slug=tt.slug,
            extended=tt.extended,
        )

        assert root_id == root.id
        self._root_tasks[root_id] = root
        self._tasks[root_id] = root
        self._disk_state[root_id] = _DiskState(content=content, extended=tt.extended)

        for child_info in subtasks:
            child = self._load_subtask(
                self.root / root.ref,
                child_info,
            )
            root.subtasks.append(child)

        invalidate_task_flags(root)

    def _load_subtask(self, root: Path, task_info: ParsedSubtask) -> Task:
        if task_info.slug is None:
            # inline task cannot be extended
            assert not task_info.extended
            task = Task(
                id=task_info.id,
                title=task_info.title,
                status=task_info.status,
                slug=task_info.slug,
                extended=task_info.extended,
            )

            # register task
            self._tasks[task.id] = task

            assert task.is_inline
            return task

        content = build_task_file_path(
            root, task_info.ref, task_info.extended
        ).read_text("utf-8")

        task, subtasks = parse_task(
            content,
            task_id=task_info.id,
            slug=task_info.slug,
            extended=task_info.extended,
        )

        self._tasks[task.id] = task
        self._disk_state[task.id] = _DiskState(
            content=content, extended=task_info.extended
        )

        for child_info in subtasks:
            child = self._load_subtask(root / task.ref, child_info)
            task.subtasks.append(child)

        return task


def _is_leaf_task(task: Task) -> bool:
    return task.is_inline or not task.subtasks


def _close_recursive(
    task: Task, new_status: TaskStatus, closed_tasks: list[Task]
) -> None:
    if task.is_closed:
        # already closed — don't override (e.g. don't cancel a done task)
        return

    closed_tasks.append(task)
    task.status = new_status

    for subtask in task.subtasks:
        _close_recursive(subtask, new_status, closed_tasks)
