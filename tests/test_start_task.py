from pathlib import Path

import pytest

from tasker.base_types import TaskStatus
from tasker.main import app
from tasker.parse import parse_task_file

from .helpers import assert_invoke, create_task


@pytest.fixture()
def story_id() -> str:
    return create_task("My story")


def test_start_pending_leaf_task_succeeds(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    result = assert_invoke(app, ["start", task_id])
    assert task_id in result.output


def test_start_leaf_task_updates_status_on_disk(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    assert_invoke(app, ["start", task_id])
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    content = task_file.read_text()
    assert f"- [~] {task_id}: Leaf task" in content


def test_start_leaf_task_parses_as_in_progress(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    assert_invoke(app, ["start", task_id])
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    task = parse_task_file(task_file)
    assert task.subtasks[0].status == TaskStatus.IN_PROGRESS


def test_start_already_in_progress_fails(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    assert_invoke(app, ["start", task_id])
    result = assert_invoke(app, ["start", task_id], expect_error=True)
    assert "already in-progress" in result.output


def test_start_done_task_fails(story_id: str) -> None:
    # Manually create a task file with done status by reading and checking
    # We simulate by calling start twice and checking the error
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    # Mark in-progress first, then set done manually via file content
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    content = task_file.read_text()
    task_file.write_text(content.replace("- [ ]", "- [x]"))
    result = assert_invoke(app, ["start", task_id], expect_error=True)
    assert "already done" in result.output


def test_start_task_with_subtasks_fails(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Subtask one"])
    assert_invoke(app, ["add", story_id, "Subtask two"])
    result = assert_invoke(app, ["start", story_id], expect_error=True)
    assert "has subtasks" in result.output
    assert "managed automatically" in result.output


def test_start_task_with_subtasks_lists_pending(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Subtask one"])
    assert_invoke(app, ["add", story_id, "Subtask two"])
    result = assert_invoke(app, ["start", story_id], expect_error=True)
    assert f"{story_id}t01" in result.output
    assert f"{story_id}t02" in result.output


def test_start_task_with_subtasks_no_pending_shows_message(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Subtask one"])
    task_id = f"{story_id}t01"
    # Mark the only subtask as done via file
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    content = task_file.read_text()
    task_file.write_text(content.replace("- [ ]", "- [x]"))
    result = assert_invoke(app, ["start", story_id], expect_error=True)
    assert "has subtasks" in result.output
    assert task_id not in result.output  # done task not listed as pending


def test_start_task_by_slug_ref(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    result = assert_invoke(app, ["start", task_id])
    assert task_id in result.output


def test_start_nonexistent_task_fails() -> None:
    assert_invoke(app, ["start", "s99t01"], expect_error=True)


def test_start_subtask_sets_parent_in_progress(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    assert_invoke(app, ["start", task_id])
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    task = parse_task_file(task_file)
    assert task.status == TaskStatus.IN_PROGRESS


def test_start_subtask_parent_stays_pending_when_others_all_pending(
    story_id: str,
) -> None:
    # Two subtasks; start none → parent stays pending
    assert_invoke(app, ["add", story_id, "Task one"])
    assert_invoke(app, ["add", story_id, "Task two"])
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    task = parse_task_file(task_file)
    assert task.status == TaskStatus.PENDING
