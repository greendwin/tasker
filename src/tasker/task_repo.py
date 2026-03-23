import re
from pathlib import Path

from tasker.base_types import (
    AnyTask,
    BasicTask,
    ExtendedTask,
    FileTask,
    InlineTask,
    TaskStatus,
)
from tasker.exceptions import TaskerError
from tasker.parse import detect_task_type, parse_task, parse_task_ref
from tasker.render import render_task, write_task_file


def generate_slug(title: str) -> str:
    words = re.sub(r"[^a-z0-9\s]", "", title.lower()).split()[:5]
    return "-".join(words)


def _derive_parent_status(subtasks: list[AnyTask]) -> TaskStatus:
    if all(t.status == TaskStatus.DONE for t in subtasks):
        return TaskStatus.DONE
    if all(t.status == TaskStatus.PENDING for t in subtasks):
        return TaskStatus.PENDING
    return TaskStatus.IN_PROGRESS


class TaskRepo:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._stories: dict[str, FileTask] = {}
        self._tasks: dict[str, AnyTask] = {}
        self._disk_content: dict[str, str] = {}

    def resolve_ref(self, task_ref: str) -> AnyTask:
        ti = parse_task_ref(task_ref)

        if ti.root_id not in self._stories:
            self._load_story(ti.root_id)

        task = self._tasks.get(ti.task_id)
        if task is None:
            raise TaskerError(
                f"Cannot resolve task reference {task_ref!r}", task_ref=task_ref
            )

        return task

    def create_story(
        self,
        *,
        title: str,
        description: str | None,
        slug: str | None,
        extended: bool,
    ) -> str:
        title = title[:1].upper() + title[1:]
        story_id = self.next_child_id(None)

        if slug is None:
            slug = generate_slug(title)

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

        self._stories[story_id] = task
        self._tasks[story_id] = task
        self._disk_content[story_id] = ""  # new — not yet on disk

        return f"{story_id}-{slug}"

    def add_subtask(self, *, task_ref: str, title: str) -> str:
        title = title[:1].upper() + title[1:]

        parent = self.resolve_ref(task_ref)
        if isinstance(parent, InlineTask):
            raise NotImplementedError("task upgrades are not supported yet")

        child_id = self.next_child_id(task_ref)
        subtask = InlineTask(
            id=child_id, title=title, status=TaskStatus.PENDING, parent=None
        )
        parent.subtasks.append(subtask)
        self._tasks[child_id] = subtask

        return child_id

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

    def propagate_status_up(self, task_id: str) -> None:
        ref = parse_task_ref(task_id)
        parent_id = ref.parent_id
        if parent_id == task_id:
            return  # root — no parent to update

        parent = self._tasks.get(parent_id)
        if not isinstance(parent, (BasicTask, ExtendedTask)):
            return

        new_status = _derive_parent_status(parent.subtasks)
        if parent.status != new_status:
            parent.status = new_status
            self.propagate_status_up(parent_id)

    def flush_tasks_to_disk(self) -> None:
        for story in self._stories.values():
            rendered = render_task(story)
            if rendered != self._disk_content.get(story.id, ""):
                write_task_file(self.root, story, content=rendered)
                self._disk_content[story.id] = rendered

    def _load_story(self, root_id: str) -> None:
        candidates = list(self.root.glob(f"{root_id}-*"))
        if not candidates:
            raise TaskerError(f"Story {root_id!r} not found", task_ref=root_id)

        if len(candidates) > 1:
            names = ", ".join(p.name for p in candidates)
            raise TaskerError(
                f"Ambiguous story {root_id!r}: multiple files match: {names}",
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

        self._stories[root_id] = task
        self._register_tasks(task)

    def _register_tasks(self, task: FileTask) -> None:
        self._tasks[task.id] = task
        for subtask in task.subtasks:
            self._tasks[subtask.id] = subtask
            if isinstance(subtask, (BasicTask, ExtendedTask)):
                self._register_tasks(subtask)
