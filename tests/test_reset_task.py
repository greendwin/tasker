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


def test_reset_in_progress_leaf_task_succeeds(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    assert_invoke(app, ["start", task_id])
    result = assert_invoke(app, ["reset", task_id])
    assert task_id in result.output


def test_reset_leaf_task_updates_status_on_disk(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    assert_invoke(app, ["start", task_id])
    assert_invoke(app, ["reset", task_id])
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    content = task_file.read_text()
    assert f"- [ ] {task_id}: Leaf task" in content


def test_reset_leaf_task_parses_as_pending(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    assert_invoke(app, ["start", task_id])
    assert_invoke(app, ["reset", task_id])
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    task = parse_task_file(task_file)
    assert task.subtasks[0].status == TaskStatus.PENDING


def test_reset_already_pending_succeeds(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    result = assert_invoke(app, ["reset", task_id])
    assert "already pending" in result.output


def test_reset_done_task(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    assert_invoke(app, ["done", task_id])
    assert_invoke(app, ["reset", task_id])
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    task = parse_task_file(task_file)
    assert task.subtasks[0].status == TaskStatus.PENDING


def test_reset_cancelled_task(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    assert_invoke(app, ["cancel", task_id])
    assert_invoke(app, ["reset", task_id])
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    task = parse_task_file(task_file)
    assert task.subtasks[0].status == TaskStatus.PENDING


def test_reset_cancelled_task_removes_strikethrough(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    assert_invoke(app, ["cancel", task_id])
    assert_invoke(app, ["reset", task_id])
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    content = task_file.read_text()
    assert f"- [ ] {task_id}: Leaf task" in content
    assert "~~" not in content


def test_reset_subtask_updates_parent_status(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Task one"])
    assert_invoke(app, ["add", story_id, "Task two"])
    assert_invoke(app, ["start", f"{story_id}t01"])
    assert_invoke(app, ["start", f"{story_id}t02"])
    # reset both — parent should go back to pending
    assert_invoke(app, ["reset", f"{story_id}t01"])
    assert_invoke(app, ["reset", f"{story_id}t02"])
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    task = parse_task_file(task_file)
    assert task.status == TaskStatus.PENDING


def test_reset_one_subtask_parent_stays_in_progress(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Task one"])
    assert_invoke(app, ["add", story_id, "Task two"])
    assert_invoke(app, ["start", f"{story_id}t01"])
    assert_invoke(app, ["start", f"{story_id}t02"])
    assert_invoke(app, ["reset", f"{story_id}t01"])
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    task = parse_task_file(task_file)
    assert task.status == TaskStatus.IN_PROGRESS


def test_reset_pending_nonleaf_succeeds(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Subtask one"])
    assert_invoke(app, ["add", story_id, "Subtask two"])
    result = assert_invoke(app, ["reset", story_id])
    assert "already pending" in result.output


def test_reset_in_progress_nonleaf_fails(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Subtask one"])
    assert_invoke(app, ["start", f"{story_id}t01"])
    result = assert_invoke(app, ["reset", story_id], expect_error=True)
    assert "has subtasks" in result.output
    assert "managed automatically" in result.output


def test_reset_nonexistent_task_fails() -> None:
    assert_invoke(app, ["reset", "s99t01"], expect_error=True)


# --- JSON output ---


def test_json_reset_outputs_task_ref(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    assert_invoke(app, ["start", task_id])
    result = assert_invoke(app, ["--json-output", "reset", task_id])
    data = json.loads(result.output)
    assert data["task_refs"] == [task_id]


def test_json_reset_nonexistent_outputs_error() -> None:
    result = assert_invoke(app, ["--json-output", "reset", "s99t01"], expect_error=True)
    data = json.loads(result.output)
    assert "error" in data


def test_json_reset_already_pending(story_id: str) -> None:
    assert_invoke(app, ["add", story_id, "Leaf task"])
    task_id = f"{story_id}t01"
    result = assert_invoke(app, ["--json-output", "reset", task_id])
    data = json.loads(result.output)
    assert data["task_refs"] == [task_id]


# --- idempotent flush on manual edit ---


def test_reset_idempotent_flushes_corrected_statuses(story_id: str) -> None:
    """Manual edit: mark subtask pending, but parent still in-progress on disk.

    Running `reset` on the subtask is idempotent (already pending), but
    the corrected parent status must still be flushed to disk.
    """
    assert_invoke(app, ["add", story_id, "Task one"])
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))

    # simulate manual edit: mark subtask in-progress but leave parent pending
    content = task_file.read_text()
    patched = content.replace("- [ ]", "- [~]").replace(
        "status: pending", "status: in-progress"
    )
    task_file.write_text(patched)

    # now reset the subtask — it was in-progress, should go to pending
    assert_invoke(app, ["reset", f"{story_id}t01"])

    # parent status must now be corrected on disk
    updated = task_file.read_text()
    assert "status: pending" in updated
