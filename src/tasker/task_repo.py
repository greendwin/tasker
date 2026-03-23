import re
from pathlib import Path

from tasker.base_types import (
    AnyTask,
    BasicTask,
    ExtendedTask,
    InlineTask,
    TaskStatus,
    is_root_task_id,
)
from tasker.exceptions import TaskHasSubtasksError, TaskValidateError
from tasker.parse import detect_task_type, parse_task, parse_task_ref
from tasker.render import render_task, write_task_file


def generate_slug(title: str) -> str:
    words = re.sub(r"[^a-z0-9\s]", "", title.lower()).split()[:5]
    return "-".join(words)


class TaskRepo:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._root_tasks: dict[str, BasicTask | ExtendedTask] = {}
        self._tasks: dict[str, AnyTask] = {}
        self._disk_content: dict[str, str] = {}

    def resolve_ref(self, task_ref: str) -> AnyTask:
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
    ) -> BasicTask | ExtendedTask:
        title = title[:1].upper() + title[1:]
        root_id = self._next_child_id(None)

        if slug is None:
            slug = generate_slug(title)

        task_type = ExtendedTask if extended else BasicTask
        task = task_type(
            id=root_id,
            slug=slug,
            title=title,
            description=description,
            status=TaskStatus.PENDING,
            subtasks=[],
        )

        self._root_tasks[root_id] = task
        self._tasks[root_id] = task
        self._disk_content[root_id] = ""  # new — not yet on disk

        return task

    def add_subtask(self, parent: AnyTask, *, title: str) -> InlineTask:
        title = title[:1].upper() + title[1:]

        if isinstance(parent, InlineTask):
            raise NotImplementedError("Task upgrades are not supported yet")

        child_id = self._next_child_id(parent)
        subtask = InlineTask(
            id=child_id,
            title=title,
            status=TaskStatus.PENDING,
        )
        parent.subtasks.append(subtask)
        self._tasks[child_id] = subtask

        return subtask

    def _next_child_id(self, parent: BasicTask | ExtendedTask | None) -> str:
        if parent is None:
            return find_next_root_task_id(self.root)

        return get_next_subtask_id(parent)

    def start_task(self, task: AnyTask) -> None:
        if not _is_leaf_task(task):
            raise TaskHasSubtasksError(task)

        task.status = TaskStatus.IN_PROGRESS
        self._update_parents_status(task)

    def cancel_task(
        self, task: AnyTask, *, force: bool = False
    ) -> list[AnyTask] | None:
        if _is_leaf_task(task):
            task.status = TaskStatus.CANCELLED
            self._update_parents_status(task)
            return None

        if not force:
            raise TaskHasSubtasksError(task)

        closed_tasks: list[AnyTask] = []
        self._close_recursive(task, TaskStatus.CANCELLED, closed_tasks)
        self._update_parents_status(task)
        return closed_tasks[1:]  # don't include root task

    def finish_task(
        self, task: AnyTask, *, force: bool = False
    ) -> list[AnyTask] | None:
        if _is_leaf_task(task):
            task.status = TaskStatus.DONE
            self._update_parents_status(task)
            return None

        if not force:
            raise TaskHasSubtasksError(task)

        closed_tasks: list[AnyTask] = []
        self._close_recursive(task, TaskStatus.DONE, closed_tasks)
        self._update_parents_status(task)
        return closed_tasks[1:]  # don't include root task

    def _close_recursive(
        self,
        task: AnyTask,
        new_status: TaskStatus,
        closed_tasks: list[AnyTask],
    ) -> None:
        if not task.is_closed:
            closed_tasks.append(task)
        task.status = new_status

        if isinstance(task, InlineTask):
            return

        for subtask in task.subtasks:
            self._close_recursive(subtask, new_status, closed_tasks)

    def _update_parents_status(self, task: AnyTask) -> None:
        cur_id = task.id
        while not is_root_task_id(cur_id):
            ri = parse_task_ref(cur_id)
            parent = self.resolve_ref(ri.parent_id)

            assert not isinstance(parent, InlineTask)
            parent.status = _get_status_from_subtasks(parent)
            cur_id = parent.id

    def flush_to_disk(self) -> None:
        for task in self._root_tasks.values():
            rendered = render_task(task)
            if rendered != self._disk_content.get(task.id, ""):
                write_task_file(self.root, task, content=rendered)
                self._disk_content[task.id] = rendered

    def _load_root_task(self, root_id: str) -> None:
        assert root_id not in self._root_tasks

        candidates = list(self.root.glob(f"{root_id}-*"))
        if not candidates:
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

        task = parse_task(
            content,
            task_id=tt.task_id,
            slug=tt.slug,
            extended=tt.extended,
        )

        self._disk_content[root_id] = content

        self._root_tasks[root_id] = task
        self._register_tasks(task)

    def _register_tasks(self, task: BasicTask | ExtendedTask) -> None:
        self._tasks[task.id] = task
        for subtask in task.subtasks:
            self._tasks[subtask.id] = subtask
            if isinstance(subtask, (BasicTask, ExtendedTask)):
                self._register_tasks(subtask)


def find_next_root_task_id(root: Path) -> str:
    existing = [
        int(m.group(1)) for p in root.iterdir() if (m := re.match(r"^s(\d+)", p.name))
    ]
    return f"s{max(existing, default=0) + 1:02d}"


def get_next_subtask_id(parent: BasicTask | ExtendedTask) -> str:
    child_prefix = parent.id if "t" in parent.id else parent.id + "t"
    existing_nums = [
        int(t.id[len(child_prefix) :])
        for t in parent.subtasks
        if t.id.startswith(child_prefix) and len(t.id) == len(child_prefix) + 2
    ]
    return f"{child_prefix}{max(existing_nums, default=0) + 1:02d}"


def _is_leaf_task(task: AnyTask) -> bool:
    if isinstance(task, InlineTask):
        return True

    return not task.subtasks


def _get_status_from_subtasks(task: BasicTask | ExtendedTask) -> TaskStatus:
    if all(t.is_closed for t in task.subtasks):
        return TaskStatus.DONE
    if any(t.status == TaskStatus.IN_PROGRESS for t in task.subtasks):
        return TaskStatus.IN_PROGRESS
    return TaskStatus.PENDING
