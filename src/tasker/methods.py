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
