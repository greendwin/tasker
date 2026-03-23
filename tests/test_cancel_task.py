import json
from pathlib import Path

import pytest

from tasker.base_types import TaskStatus
from tasker.main import app
from tasker.parse import parse_task_file

from .helpers import assert_invoke, create_task


@pytest.fixture()
def story_id() -> str:
    return create_task("My story")


def test_cancel_pending_leaf_task_succeeds(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    result = assert_invoke(app, ["cancel", task_id])
    assert task_id in result.output


def test_cancel_leaf_task_updates_status_on_disk(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    assert_invoke(app, ["cancel", task_id])
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    content = task_file.read_text()
    assert f"- [x] {task_id}: ~~Leaf task~~" in content


def test_cancel_leaf_task_parses_as_cancelled(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    assert_invoke(app, ["cancel", task_id])
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    task = parse_task_file(task_file)
    assert task.subtasks[0].status == TaskStatus.CANCELLED


def test_cancel_preserves_title_without_strikethrough(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    assert_invoke(app, ["cancel", task_id])
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    task = parse_task_file(task_file)
    assert task.subtasks[0].title == "Leaf task"


def test_cancel_already_cancelled_succeeds(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    assert_invoke(app, ["cancel", task_id])
    result = assert_invoke(app, ["cancel", task_id])
    assert "already cancelled" in result.output


def test_cancel_in_progress_task(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    assert_invoke(app, ["start", task_id])
    assert_invoke(app, ["cancel", task_id])
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    task = parse_task_file(task_file)
    assert task.subtasks[0].status == TaskStatus.CANCELLED


def test_cancel_done_task(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    assert_invoke(app, ["done", task_id])
    result = assert_invoke(app, ["cancel", task_id])
    assert "cancelled" in result.output
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    task = parse_task_file(task_file)
    assert task.subtasks[0].status == TaskStatus.CANCELLED


def test_cancel_subtask_sets_parent_done_when_only_subtask(
    story_id: str,
) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    assert_invoke(app, ["cancel", task_id])
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    task = parse_task_file(task_file)
    assert task.status == TaskStatus.DONE


def test_cancel_subtask_parent_stays_pending_when_sibling_pending(
    story_id: str,
) -> None:
    assert_invoke(app, ["add", story_id, "Task one"])
    assert_invoke(app, ["add", story_id, "Task two"])
    task_id = f"{story_id}t01"
    assert_invoke(app, ["cancel", task_id])
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    task = parse_task_file(task_file)
    assert task.status == TaskStatus.PENDING


def test_cancel_task_with_subtasks_fails(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Subtask one"])
    assert_invoke(app, ["add", story_id, "Subtask two"])
    result = assert_invoke(app, ["cancel", story_id], expect_error=True)
    assert "has subtasks" in result.output
    assert "managed automatically" in result.output


def test_cancel_nonleaf_hints_force(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Subtask one"])
    result = assert_invoke(app, ["cancel", story_id], expect_error=True)
    assert "--force" in result.output


def test_cancel_force_succeeds_with_open_subtasks(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Subtask one"])
    assert_invoke(app, ["add", story_id, "Subtask two"])
    assert_invoke(app, ["cancel", "--force", story_id])


def test_cancel_force_marks_all_subtasks_cancelled(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Subtask one"])
    assert_invoke(app, ["add", story_id, "Subtask two"])
    assert_invoke(app, ["cancel", "--force", story_id])
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    task = parse_task_file(task_file)
    assert all(t.status == TaskStatus.CANCELLED for t in task.subtasks)


def test_cancel_force_marks_parent_cancelled(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Subtask one"])
    assert_invoke(app, ["add", story_id, "Subtask two"])
    assert_invoke(app, ["cancel", "--force", story_id])
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    task = parse_task_file(task_file)
    assert task.status == TaskStatus.CANCELLED


def test_cancel_force_prints_forcibly_cancelled_subtasks(
    story_id: str,
) -> None:
    assert_invoke(app, ["add", story_id, "Subtask one"])
    assert_invoke(app, ["add", story_id, "Subtask two"])
    result = assert_invoke(app, ["cancel", "--force", story_id])
    assert f"{story_id}t01" in result.output
    assert f"{story_id}t02" in result.output


def test_cancel_force_does_not_list_already_cancelled_subtasks(
    story_id: str,
) -> None:
    assert_invoke(app, ["add", story_id, "Subtask one"])
    assert_invoke(app, ["add", story_id, "Subtask two"])
    assert_invoke(app, ["cancel", f"{story_id}t01"])
    result = assert_invoke(app, ["cancel", "--force", story_id])
    assert f"{story_id}t01" not in result.output
    assert f"{story_id}t02" in result.output


def test_cancel_nonexistent_task_fails() -> None:
    assert_invoke(app, ["cancel", "s99t01"], expect_error=True)


def test_cancel_force_on_leaf_task_works(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    assert_invoke(app, ["cancel", "--force", task_id])
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    task = parse_task_file(task_file)
    assert task.subtasks[0].status == TaskStatus.CANCELLED


# --- done --force skips cancelled subtasks ---


def test_done_force_skips_cancelled_subtasks(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Subtask one"])
    assert_invoke(app, ["add", story_id, "Subtask two"])
    assert_invoke(app, ["cancel", f"{story_id}t01"])
    result = assert_invoke(app, ["done", "--force", story_id])
    assert f"{story_id}t01" not in result.output
    assert f"{story_id}t02" in result.output


# --- JSON output ---


def test_json_cancel_outputs_task_ref(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    result = assert_invoke(app, ["--json-output", "cancel", task_id])
    data = json.loads(result.output)
    assert data["task_ref"] == task_id


def test_json_cancel_force_includes_forced_task_ids(
    story_id: str,
) -> None:
    assert_invoke(app, ["add", story_id, "Subtask one"])
    assert_invoke(app, ["add", story_id, "Subtask two"])
    result = assert_invoke(app, ["--json-output", "cancel", "--force", story_id])
    data = json.loads(result.output)
    assert set(data["forced_task_ids"]) == {
        f"{story_id}t01",
        f"{story_id}t02",
    }


def test_json_cancel_nonexistent_outputs_error() -> None:
    result = assert_invoke(
        app, ["--json-output", "cancel", "s99t01"], expect_error=True
    )
    data = json.loads(result.output)
    assert "error" in data
