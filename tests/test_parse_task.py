from pathlib import Path

from tasker.data import Task, TaskStatus, parse_task

_DIR = Path("/tasks")


def _write_task(
    name: str,
    title: str,
    description: str | None = None,
    status: str = "pending",
) -> Path:
    _DIR.mkdir(exist_ok=True)
    underline = "=" * len(title)
    desc_block = f"\n{description}\n" if description else ""
    content = f"{title}\n{underline}\n{desc_block}\n## Props\n\nStatus: {status}\n"
    path = _DIR / name
    path.write_text(content)
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
    task = parse_task(_write_task("s01-my-task.md", "My task", status="in-progress"))
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
    (story_dir / "README.md").write_text(
        "My task\n=======\n\n## Props\n\nStatus: pending\n"
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
    bad.write_text("Title\n=====\n\n## Props\n\nStatus: pending\n")
    try:
        parse_task(bad)
        assert False, "expected ValueError"
    except ValueError:
        pass
