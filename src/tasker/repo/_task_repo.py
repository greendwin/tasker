import shutil
from dataclasses import dataclass
from pathlib import Path

from tasker.base_types import Task, TaskStatus, is_root_task_id
from tasker.exceptions import TaskArchivedError, TaskHasSubtasksError, TaskValidateError
from tasker.parse import ParsedSubtask, detect_task_type, parse_task, parse_task_ref
from tasker.render import build_task_file_path, render_task, write_task_file

from ._move_task import TaskRename, move_task_impl
from ._utils import (
    find_next_root_task_id,
    generate_slug,
    get_next_subtask_id,
    get_status_from_subtasks,
    has_file_subtasks,
    invalidate_task_flags,
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
        self._update_parents_status(subtask)

        return subtask

    def _next_child_id(self, parent: Task | None) -> str:
        if parent is None:
            return find_next_root_task_id(self.root, self.archive_root)

        return get_next_subtask_id(parent)

    def start_task(self, task: Task) -> None:
        if not _is_leaf_task(task):
            raise TaskHasSubtasksError(task)

        task.status = TaskStatus.IN_PROGRESS
        self._update_parents_status(task)

    def reset_task(self, task: Task) -> None:
        if not _is_leaf_task(task):
            raise TaskHasSubtasksError(task)

        task.status = TaskStatus.PENDING
        self._update_parents_status(task)

    def cancel_task(self, task: Task, *, force: bool = False) -> list[Task] | None:
        if _is_leaf_task(task):
            task.status = TaskStatus.CANCELLED
            self._update_parents_status(task)
            return None

        if not force:
            raise TaskHasSubtasksError(task)

        closed_tasks: list[Task] = []
        self._close_recursive(task, TaskStatus.CANCELLED, closed_tasks)
        self._update_parents_status(task)
        return closed_tasks[1:]  # don't include root task

    def finish_task(self, task: Task, *, force: bool = False) -> list[Task] | None:
        if _is_leaf_task(task):
            task.status = TaskStatus.DONE
            self._update_parents_status(task)
            return None

        if not force:
            raise TaskHasSubtasksError(task)

        closed_tasks: list[Task] = []
        self._close_recursive(task, TaskStatus.DONE, closed_tasks)
        self._update_parents_status(task)
        return closed_tasks[1:]  # don't include root task

    def _close_recursive(
        self,
        task: Task,
        new_status: TaskStatus,
        closed_tasks: list[Task],
    ) -> None:
        if task.is_closed:
            # already closed — don't override (e.g. don't cancel a done task)
            return

        closed_tasks.append(task)
        task.status = new_status

        for subtask in task.subtasks:
            self._close_recursive(subtask, new_status, closed_tasks)

    def _update_parents_status(self, task: Task) -> None:
        cur_id = task.id
        while not is_root_task_id(cur_id):
            ri = parse_task_ref(cur_id)
            parent = self.resolve_ref(ri.parent_id)

            assert not parent.is_inline
            parent.status = get_status_from_subtasks(parent)
            parent.extended = parent.extended or has_file_subtasks(parent)
            cur_id = parent.id

    def archive_task(self, task: Task, *, force: bool = False) -> list[Task] | None:
        if not is_root_task_id(task.id):
            raise TaskValidateError(
                f"Only root tasks can be archived, {task.id!r} is a subtask.",
                task_ref=task.ref,
            )

        forced: list[Task] | None = None
        if not task.is_closed:
            if not force:
                raise TaskValidateError(
                    f"Task {task.id!r} is not closed. "
                    "Use --force to cancel open subtasks and archive.",
                    task_ref=task.id,
                )
            forced = self.cancel_task(task, force=True)

        # flush before moving so files are up-to-date
        self.flush_to_disk()

        self.archive_root.mkdir(exist_ok=True)

        # move task file(s) to archive
        if task.extended:
            src = self.root / task.ref
            dst = self.archive_root / task.ref
            shutil.move(str(src), str(dst))
        else:
            src = self.root / f"{task.ref}.md"
            dst = self.archive_root / f"{task.ref}.md"
            shutil.move(str(src), str(dst))

        return forced

    def unarchive_task(self, task_ref: str) -> str:
        ti = parse_task_ref(task_ref)

        if not is_root_task_id(ti.task_id):
            raise TaskValidateError(
                f"Only root tasks can be unarchived, {ti.task_id!r} is a subtask.",
                task_ref=task_ref,
            )

        candidates = list(self.archive_root.glob(f"{ti.root_id}-*"))
        if not candidates:
            raise TaskValidateError(
                f"Task {ti.root_id!r} not found in archive.",
                task_ref=ti.root_id,
            )

        src = candidates[0]
        dst = self.root / src.name
        shutil.move(str(src), str(dst))

        return src.name

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
