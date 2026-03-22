from pathlib import Path

from tasker.task import Task, TaskStatus, parse_task
from tasker.generate import render_task_file

_DIR = Path("/tasks")


def _write_task(
    name: str,
    title: str,
    description: str | None = None,
    status: TaskStatus = TaskStatus.PENDING,
) -> Path:
    _DIR.mkdir(exist_ok=True)
    stem = name.removesuffix(".md")
    path = _DIR / name
    render_task_file(
        path,
        Task(
            id=stem.split("-", 1)[0],
            slug=stem.split("-", 1)[1],
            title=title,
            description=description,
            status=status,
            subtasks=[],
            loaded=True,
            filename=stem,
        ),
    )
    return path


def test_parse_title() -> None:
    task = parse_task(_write_task("s01-my-task.md", "My task"))
    assert task.title == "My task"


def test_parse_id_and_slug() -> None:
    task = parse_task(_write_task("s01-my-task.md", "My task"))
    assert task.id == "s01"
    assert task.slug == "my-task"


def test_parse_status_pending() -> None:
    task = parse_task(_write_task("s01-my-task.md", "My task"))
    assert task.status == TaskStatus.PENDING


def test_parse_status_in_progress() -> None:
    task = parse_task(_write_task("s01-my-task.md", "My task", status=TaskStatus.IN_PROGRESS))
    assert task.status == TaskStatus.IN_PROGRESS


def test_parse_no_description() -> None:
    task = parse_task(_write_task("s01-my-task.md", "My task"))
    assert task.description is None


def test_parse_description() -> None:
    task = parse_task(_write_task("s01-my-task.md", "My task", description="Some details"))
    assert task.description == "Some details"


def test_parse_multiline_description() -> None:
    task = parse_task(
        _write_task("s01-my-task.md", "My task", description="Line one\nLine two")
    )
    assert task.description == "Line one\nLine two"


def test_parse_simple_file_not_detailed() -> None:
    task = parse_task(_write_task("s01-my-task.md", "My task"))
    assert task.detailed is False


def test_parse_detailed_dir() -> None:
    _DIR.mkdir(exist_ok=True)
    story_dir = _DIR / "s01-my-task"
    story_dir.mkdir()
    render_task_file(
        story_dir / "README.md",
        Task(id="s01", slug="my-task", title="My task", status=TaskStatus.PENDING, subtasks=[], loaded=True, filename="s01-my-task"),
    )
    task = parse_task(story_dir)
    assert task.detailed is True
    assert task.id == "s01"
    assert task.slug == "my-task"


def test_parse_returns_task_model() -> None:
    task = parse_task(_write_task("s01-my-task.md", "My task"))
    assert isinstance(task, Task)


def test_parse_invalid_filename_raises() -> None:
    _DIR.mkdir(exist_ok=True)
    bad = _DIR / "bad-name.md"
    render_task_file(
        bad,
        Task(id="bad", slug="name", title="Title", status=TaskStatus.PENDING, subtasks=[], loaded=True, filename="bad-name"),
    )
    try:
        parse_task(bad)
        assert False, "expected ValueError"
    except ValueError:
        pass
