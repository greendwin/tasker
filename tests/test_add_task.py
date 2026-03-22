from pathlib import Path

import pytest

from tasker.base_types import TaskStatus
from tasker.main import app
from tasker.parse import parse_task

from .helpers import assert_invoke, create_task


@pytest.fixture()
def parent_id() -> str:
    return create_task("My story")


def test_add_inline_subtask_output(parent_id: str) -> None:
    result = assert_invoke(app, ["add", parent_id, "Define task forms"])
    assert f"{parent_id}t01" in result.output


def test_add_subtask_file_contains_entry(parent_id: str) -> None:
    assert_invoke(app, ["add", parent_id, "Define task forms"])
    task_file = next(Path("planning").glob(f"{parent_id}-*.md"))
    content = task_file.read_text()
    assert f"- [ ] {parent_id}t01: Define task forms" in content


def test_add_multiple_subtasks_increments_id(parent_id: str) -> None:
    assert_invoke(app, ["add", parent_id, "First subtask"])
    result = assert_invoke(app, ["add", parent_id, "Second subtask"])
    assert f"{parent_id}t02" in result.output
    task_file = next(Path("planning").glob(f"{parent_id}-*.md"))
    content = task_file.read_text()
    assert f"- [ ] {parent_id}t01: First subtask" in content
    assert f"- [ ] {parent_id}t02: Second subtask" in content


def test_add_subtask_parent_not_found() -> None:
    assert_invoke(app, ["add", "s99", "Some task"], expect_error=True)


def test_add_subtask_strips_slug_from_parent_id(parent_id: str) -> None:
    task_file = next(Path("planning").glob(f"{parent_id}-*.md"))
    slug_ref = task_file.stem  # e.g. "s01-my-story"
    result = assert_invoke(app, ["add", slug_ref, "Define task forms"])
    assert f"{parent_id}t01" in result.output


def test_add_subtask_title_is_capitalized(parent_id: str) -> None:
    assert_invoke(app, ["add", parent_id, "define task forms"])
    task_file = next(Path("planning").glob(f"{parent_id}-*.md"))
    content = task_file.read_text()
    assert f"- [ ] {parent_id}t01: Define task forms" in content


def test_add_subtask_parse_roundtrip(parent_id: str) -> None:
    assert_invoke(app, ["add", parent_id, "First subtask"])
    assert_invoke(app, ["add", parent_id, "Second subtask"])
    task_file = next(Path("planning").glob(f"{parent_id}-*.md"))
    task = parse_task(task_file)
    assert len(task.subtasks) == 2
    assert task.subtasks[0].id == f"{parent_id}t01"
    assert task.subtasks[0].title == "First subtask"
    assert task.subtasks[0].status == TaskStatus.PENDING
    assert task.subtasks[1].id == f"{parent_id}t02"
    assert task.subtasks[1].title == "Second subtask"
