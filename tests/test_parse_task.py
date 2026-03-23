from pathlib import Path

import pytest

from tasker.base_types import BasicTask, ExtendedTask, FileTaskBase, TaskStatus
from tasker.exceptions import TaskValidateError
from tasker.parse import parse_task_file
from tasker.render import render_task, write_task_file

_DIR = Path("/tmp/tasks")


def _write_task(
    name: str,
    title: str,
    description: str | None = None,
    status: TaskStatus = TaskStatus.PENDING,
) -> Path:
    _DIR.mkdir(exist_ok=True)
    stem = name.removesuffix(".md")
    task_id, slug = stem.split("-", 1)
    task = BasicTask(
        parent=None,
        id=task_id,
        slug=slug,
        title=title,
        description=description,
        status=status,
        subtasks=[],
    )
    write_task_file(_DIR, task, content=render_task(task))
    return _DIR / name


def test_parse_title() -> None:
    task = parse_task_file(_write_task("s01-my-task.md", "My task"))
    assert task.title == "My task"


def test_parse_id_and_slug() -> None:
    task = parse_task_file(_write_task("s01-my-task.md", "My task"))
    assert task.id == "s01"
    assert task.slug == "my-task"


def test_parse_status_pending() -> None:
    task = parse_task_file(_write_task("s01-my-task.md", "My task"))
    assert task.status == TaskStatus.PENDING


def test_parse_status_in_progress() -> None:
    task = parse_task_file(
        _write_task("s01-my-task.md", "My task", status=TaskStatus.IN_PROGRESS)
    )
    assert task.status == TaskStatus.IN_PROGRESS


def test_parse_no_description() -> None:
    task = parse_task_file(_write_task("s01-my-task.md", "My task"))
    assert task.description is None


def test_parse_description() -> None:
    task = parse_task_file(
        _write_task("s01-my-task.md", "My task", description="Some details")
    )
    assert task.description == "Some details"


def test_parse_multiline_description() -> None:
    task = parse_task_file(
        _write_task("s01-my-task.md", "My task", description="Line one\nLine two")
    )
    assert task.description == "Line one\nLine two"


def test_parse_simple_file_is_basic() -> None:
    task = parse_task_file(_write_task("s01-my-task.md", "My task"))
    assert isinstance(task, BasicTask)


def test_parse_detailed_dir() -> None:
    _DIR.mkdir(exist_ok=True)
    task = ExtendedTask(
        parent=None,
        id="s01",
        slug="my-task",
        title="My task",
        status=TaskStatus.PENDING,
        subtasks=[],
    )
    write_task_file(_DIR, task, content=render_task(task))

    parsed = parse_task_file(_DIR / "s01-my-task")
    assert isinstance(parsed, ExtendedTask)
    assert parsed.id == "s01"
    assert parsed.slug == "my-task"


def test_parse_returns_file_task() -> None:
    task = parse_task_file(_write_task("s01-my-task.md", "My task"))
    assert isinstance(task, FileTaskBase)


def test_parse_invalid_filename_raises() -> None:
    _DIR.mkdir(exist_ok=True)
    bad = _DIR / "bad-name.md"
    bad.write_text("Title\n=====\n\n## Props\n\nStatus: pending\n")
    with pytest.raises(TaskValidateError):
        parse_task_file(bad)


# --- front-matter format tests ---


def test_file_has_front_matter_delimiters() -> None:
    path = _write_task("s01-my-task.md", "My task")
    content = path.read_text()
    assert content.startswith("---\n")
    assert "---\n" in content[4:]  # closing delimiter


def test_file_front_matter_has_id() -> None:
    path = _write_task("s01-my-task.md", "My task")
    content = path.read_text()
    assert "id: s01" in content


def test_file_front_matter_has_status() -> None:
    path = _write_task("s01-my-task.md", "My task")
    content = path.read_text()
    assert "status: pending" in content


def test_file_has_no_props_section() -> None:
    path = _write_task("s01-my-task.md", "My task")
    content = path.read_text()
    assert "## Props" not in content


def test_file_title_uses_atx_heading() -> None:
    path = _write_task("s01-my-task.md", "My task")
    content = path.read_text()
    assert "# My task" in content


def test_file_title_has_no_underline() -> None:
    path = _write_task("s01-my-task.md", "My task")
    content = path.read_text()
    assert "=======" not in content


def test_parse_raises_on_non_heading_title() -> None:
    _DIR.mkdir(exist_ok=True)
    bad = _DIR / "s01-my-task.md"
    bad.write_text("---\nid: s01\nstatus: pending\n---\n\nMy task\n=======\n")
    with pytest.raises(TaskValidateError):
        parse_task_file(bad)


def test_parse_raises_on_missing_front_matter() -> None:
    _DIR.mkdir(exist_ok=True)
    bad = _DIR / "s01-my-task.md"
    bad.write_text("My task\n=======\n\nStatus: pending\n")
    with pytest.raises(TaskValidateError):
        parse_task_file(bad)


def test_parse_raises_on_unclosed_front_matter() -> None:
    _DIR.mkdir(exist_ok=True)
    bad = _DIR / "s01-my-task.md"
    bad.write_text("---\nid: s01\nstatus: pending\n")
    with pytest.raises(TaskValidateError):
        parse_task_file(bad)


# --- task_ref context on parse errors ---


def test_parse_error_has_task_ref() -> None:
    _DIR.mkdir(exist_ok=True)
    bad = _DIR / "s01-my-task.md"
    bad.write_text("---\nid: s01\nstatus: pending\n---\n\nMy task\n=======\n")
    with pytest.raises(TaskValidateError) as exc_info:
        parse_task_file(bad)
    assert exc_info.value.task_ref is not None


def test_parse_error_task_ref_contains_filename() -> None:
    _DIR.mkdir(exist_ok=True)
    bad = _DIR / "s01-my-task.md"
    bad.write_text("---\nid: s01\nstatus: pending\n---\n\nMy task\n=======\n")
    with pytest.raises(TaskValidateError) as exc_info:
        parse_task_file(bad)
    assert "s01-my-task" in (exc_info.value.task_ref or "")


def test_parse_invalid_filename_error_has_task_ref() -> None:
    _DIR.mkdir(exist_ok=True)
    bad = _DIR / "bad-name.md"
    bad.write_text("")
    with pytest.raises(TaskValidateError) as exc_info:
        parse_task_file(bad)
    assert exc_info.value.task_ref is not None
