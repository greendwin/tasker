from pathlib import Path

import pytest

from tasker.base_types import TaskStatus
from tasker.main import app
from tasker.parse import parse_task_file

from .helpers import assert_invoke, create_task


@pytest.fixture()
def story_id() -> str:
    return create_task("My story")


def test_stop_pending_leaf_task_succeeds(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    result = assert_invoke(app, ["done", task_id])
    assert task_id in result.output


def test_stop_leaf_task_updates_status_on_disk(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    assert_invoke(app, ["done", task_id])
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    content = task_file.read_text()
    assert f"- [x] {task_id}: Leaf task" in content


def test_stop_leaf_task_parses_as_done(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    assert_invoke(app, ["done", task_id])
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    task = parse_task_file(task_file)
    assert task.subtasks[0].status == TaskStatus.DONE


def test_stop_already_done_task_succeeds(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    assert_invoke(app, ["done", task_id])
    result = assert_invoke(app, ["done", task_id])
    assert "already finished" in result.output


def test_stop_in_progress_task_marks_done(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    assert_invoke(app, ["start", task_id])
    assert_invoke(app, ["done", task_id])
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    task = parse_task_file(task_file)
    assert task.subtasks[0].status == TaskStatus.DONE


def test_stop_subtask_sets_parent_done_when_only_subtask(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    assert_invoke(app, ["done", task_id])
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    task = parse_task_file(task_file)
    assert task.status == TaskStatus.DONE


def test_stop_subtask_parent_stays_in_progress_when_sibling_pending(
    story_id: str,
) -> None:
    assert_invoke(app, ["add", story_id, "Task one"])
    assert_invoke(app, ["add", story_id, "Task two"])
    task_id = f"{story_id}t01"
    assert_invoke(app, ["done", task_id])
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    task = parse_task_file(task_file)
    assert task.status == TaskStatus.PENDING


def test_stop_task_with_subtasks_fails(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Subtask one"])
    assert_invoke(app, ["add", story_id, "Subtask two"])
    result = assert_invoke(app, ["done", story_id], expect_error=True)
    assert "has subtasks" in result.output
    assert "managed automatically" in result.output


def test_stop_task_with_subtasks_lists_pending(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Subtask one"])
    assert_invoke(app, ["add", story_id, "Subtask two"])
    result = assert_invoke(app, ["done", story_id], expect_error=True)
    assert f"{story_id}t01" in result.output
    assert f"{story_id}t02" in result.output


def test_stop_nonexistent_task_fails() -> None:
    assert_invoke(app, ["done", "s99t01"], expect_error=True)
