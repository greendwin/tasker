import re
from pathlib import Path

from tasker.base_types import AnyTask, BasicTask, ExtendedTask, FileTask, InlineTask
from tasker.exceptions import TaskerError
from tasker.parse import parse_task, parse_task_ref


def generate_slug(title: str) -> str:
    words = re.sub(r"[^a-z0-9\s]", "", title.lower()).split()[:5]
    return "-".join(words)


class TaskRepo:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._stories: dict[str, FileTask] = {}
        self._tasks: dict[str, AnyTask] = {}

    def resolve_ref(self, task_ref: str) -> AnyTask:
        ti = parse_task_ref(task_ref)

        # load corresponding story tree
        if ti.root_id not in self._stories:
            self._load_story(ti.root_id)

        task = self._tasks.get(ti.task_id)
        if task is None:
            raise TaskerError(
                f"Cannot resolve task reference {task_ref!r}", task_ref=task_ref
            )

        return task

    def next_child_id(self, task_ref: str | None) -> str:
        if task_ref is None:
            existing = [
                int(m.group(1))
                for p in self.root.iterdir()
                if (m := re.match(r"^s(\d+)", p.name))
            ]
            return f"s{max(existing, default=0) + 1:02d}"

        parent = self.resolve_ref(task_ref)
        if isinstance(parent, InlineTask):
            raise TaskerError(
                f"Cannot add subtask to inline task {task_ref!r}", task_ref=task_ref
            )
        parent_id = parent.id
        child_prefix = parent_id if "t" in parent_id else parent_id + "t"
        existing_nums = [
            int(t.id[len(child_prefix) :])
            for t in parent.subtasks
            if t.id.startswith(child_prefix) and len(t.id) == len(child_prefix) + 2
        ]
        return f"{child_prefix}{max(existing_nums, default=0) + 1:02d}"

    def _load_story(self, root_id: str) -> None:
        candidates = list(self.root.glob(f"{root_id}-*"))
        if not candidates:
            raise TaskerError(f"Story {root_id!r} not found", task_ref=root_id)
        story = parse_task(candidates[0])
        self._stories[root_id] = story
        self._register_tasks(story)

    def _register_tasks(self, task: FileTask) -> None:
        self._tasks[task.id] = task
        for subtask in task.subtasks:
            self._tasks[subtask.id] = subtask
            if isinstance(subtask, (BasicTask, ExtendedTask)):
                self._register_tasks(subtask)
