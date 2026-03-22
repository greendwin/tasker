from pathlib import Path

from tasker.main import app
from tasker.task import TaskStatus, parse_task

from .helpers import assert_invoke


def _create_parent(title: str = "My story") -> None:
    assert_invoke(app, ["new", title])


def test_add_inline_subtask_output() -> None:
    _create_parent()
    result = assert_invoke(app, ["add", "s01", "Define task forms"])
    assert "s01t01" in result.output


def test_add_subtask_file_contains_entry() -> None:
    _create_parent()
    assert_invoke(app, ["add", "s01", "Define task forms"])
    content = Path("planning/s01-my-story.md").read_text()
    assert "- [ ] s01t01: Define task forms" in content


def test_add_multiple_subtasks_increments_id() -> None:
    _create_parent()
    assert_invoke(app, ["add", "s01", "First subtask"])
    result = assert_invoke(app, ["add", "s01", "Second subtask"])
    assert "s01t02" in result.output
    content = Path("planning/s01-my-story.md").read_text()
    assert "- [ ] s01t01: First subtask" in content
    assert "- [ ] s01t02: Second subtask" in content


def test_add_subtask_parent_not_found() -> None:
    assert_invoke(app, ["add", "s99", "Some task"], expect_error=True)


def test_add_subtask_strips_slug_from_parent_id() -> None:
    _create_parent()
    result = assert_invoke(app, ["add", "s01-my-story", "Define task forms"])
    assert "s01t01" in result.output


def test_add_subtask_title_is_capitalized() -> None:
    _create_parent()
    assert_invoke(app, ["add", "s01", "define task forms"])
    content = Path("planning/s01-my-story.md").read_text()
    assert "- [ ] s01t01: Define task forms" in content


def test_add_subtask_parse_roundtrip() -> None:
    _create_parent()
    assert_invoke(app, ["add", "s01", "First subtask"])
    assert_invoke(app, ["add", "s01", "Second subtask"])
    task = parse_task(Path("planning/s01-my-story.md"))
    assert len(task.subtasks) == 2
    assert task.subtasks[0].id == "s01t01"
    assert task.subtasks[0].title == "First subtask"
    assert task.subtasks[0].status == TaskStatus.PENDING
    assert task.subtasks[1].id == "s01t02"
    assert task.subtasks[1].title == "Second subtask"
