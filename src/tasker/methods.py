from tasker.base_types import BasicTask, ExtendedTask, TaskStatus
from tasker.exceptions import TaskerError, TaskHasSubtasksError
from tasker.task_repo import TaskRepo


def create_new_story(
    repo: TaskRepo,
    *,
    title: str,
    description: str | None,
    slug: str | None,
    extended: bool,
) -> str:
    filename = repo.create_story(
        title=title, description=description, slug=slug, extended=extended
    )
    repo.flush_tasks_to_disk()
    return filename


def add_subtask(repo: TaskRepo, *, task_ref: str, title: str) -> str:
    child_id = repo.add_subtask(task_ref=task_ref, title=title)
    repo.flush_tasks_to_disk()
    return child_id


def start_task(repo: TaskRepo, *, task_ref: str) -> str:
    task = repo.resolve_ref(task_ref)

    if isinstance(task, (BasicTask, ExtendedTask)) and task.subtasks:
        pending = [
            (t.id, t.title) for t in task.subtasks if t.status == TaskStatus.PENDING
        ]
        raise TaskHasSubtasksError(task.id, pending_subtasks=pending)

    if task.status == TaskStatus.IN_PROGRESS:
        raise TaskerError(f"Task {task.id!r} is already in-progress.", task_ref=task.id)

    if task.status == TaskStatus.DONE:
        raise TaskerError(f"Task {task.id!r} is already done.", task_ref=task.id)

    task.status = TaskStatus.IN_PROGRESS
    repo.propagate_status_up(task.id)
    repo.flush_tasks_to_disk()
    return task.id
