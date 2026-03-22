from tasker.base_types import BasicTask, ExtendedTask, InlineTask, TaskStatus
from tasker.render import render_task_file
from tasker.task_repo import TaskRepo, generate_slug


def create_new_story(
    repo: TaskRepo,
    *,
    title: str,
    description: str | None,
    slug: str | None,
    extended: bool,
) -> str:
    root = repo.root

    # make sure that title starts with upper letter
    title = title[:1].upper() + title[1:]

    story_id = repo.next_child_id(None)

    if slug is None:
        slug = generate_slug(title)
    filename = f"{story_id}-{slug}"

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

    render_task_file(root, task)

    return filename


def add_subtask(repo: TaskRepo, *, task_ref: str, title: str) -> str:
    root = repo.root

    # make sure that title starts with upper letter
    title = title[:1].upper() + title[1:]

    parent = repo.resolve_ref(task_ref)
    if isinstance(parent, InlineTask):
        raise NotImplementedError("task upgrades are not supported yet")

    child_id = repo.next_child_id(task_ref)

    parent.subtasks.append(
        InlineTask(id=child_id, title=title, status=TaskStatus.PENDING, parent=None)
    )

    render_task_file(root, parent)
    return child_id
