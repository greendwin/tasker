import json
from pathlib import Path

import pytest

from tasker.base_types import TaskStatus
from tasker.cli import app
from tasker.parse import parse_task_file

from .helpers import add_subtask, assert_invoke, create_task


@pytest.fixture()
def story_id() -> str:
    return create_task("My story").task_id


# --- basic archive ---


def test_archive_done_task(story_id: str) -> None:
    assert_invoke(app, ["done", "--force", story_id])
    result = assert_invoke(app, ["archive", story_id])
    assert "archived" in result.output


def test_archive_cancelled_task(story_id: str) -> None:
    assert_invoke(app, ["cancel", "--force", story_id])
    result = assert_invoke(app, ["archive", story_id])
    assert "archived" in result.output


def test_archive_moves_basic_file_to_archive(story_id: str) -> None:
    assert_invoke(app, ["done", "--force", story_id])
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    filename = task_file.name
    assert_invoke(app, ["archive", story_id])
    assert not task_file.exists()
    assert (Path("planning") / "archive" / filename).exists()


def test_archive_moves_extended_dir_to_archive(story_id: str) -> None:
    add_subtask(story_id, "Subtask", details="Some details")
    assert_invoke(app, ["done", "--force", story_id])
    story_dir = next(Path("planning").glob(f"{story_id}-*/"))
    dirname = story_dir.name
    assert_invoke(app, ["archive", story_id])
    assert not story_dir.exists()
    assert (Path("planning") / "archive" / dirname).is_dir()
    assert (Path("planning") / "archive" / dirname / "README.md").exists()


# --- task must be closed ---


def test_archive_pending_task_fails(story_id: str) -> None:
    result = assert_invoke(app, ["archive", story_id], expect_error=True)
    assert "not closed" in result.output


def test_archive_open_task_lists_open_subtasks(story_id: str) -> None:
    t01 = add_subtask(story_id, "Open subtask").task_id
    t02 = add_subtask(story_id, "Another open").task_id
    result = assert_invoke(app, ["archive", story_id], expect_error=True)
    assert "not closed" in result.output
    assert t01 in result.output
    assert t02 in result.output
    assert "--force" in result.output


def test_archive_in_progress_task_fails(story_id: str) -> None:
    t01 = add_subtask(story_id, "Task").task_id
    assert_invoke(app, ["start", t01])
    result = assert_invoke(app, ["archive", story_id], expect_error=True)
    assert "not closed" in result.output


def test_archive_subtask_fails(story_id: str) -> None:
    t01 = add_subtask(story_id, "Subtask").task_id
    assert_invoke(app, ["done", t01])
    result = assert_invoke(app, ["archive", t01], expect_error=True)
    assert "root" in result.output.lower()
    assert "subtask" in result.output.lower()


# --- --force cancels open subtasks ---


def test_archive_force_pending_task(story_id: str) -> None:
    add_subtask(story_id, "Subtask one")
    add_subtask(story_id, "Subtask two")
    result = assert_invoke(app, ["archive", "--force", story_id])
    assert "archived" in result.output


def test_archive_force_cancels_subtasks(story_id: str) -> None:
    t01 = add_subtask(story_id, "Subtask one").task_id
    t02 = add_subtask(story_id, "Subtask two").task_id
    result = assert_invoke(app, ["archive", "--force", story_id])
    assert t01 in result.output
    assert t02 in result.output


def test_archive_force_moves_file(story_id: str) -> None:
    add_subtask(story_id, "Subtask")
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    filename = task_file.name
    assert_invoke(app, ["archive", "--force", story_id])
    assert not task_file.exists()
    assert (Path("planning") / "archive" / filename).exists()


def test_archive_force_preserves_done_subtasks(story_id: str) -> None:
    t01 = add_subtask(story_id, "Done task").task_id
    add_subtask(story_id, "Open task")
    assert_invoke(app, ["done", t01])
    result = assert_invoke(app, ["archive", "--force", story_id])
    # only open task was forcibly cancelled
    assert t01 not in result.output

    archived_file = next((Path("planning") / "archive").glob(f"{story_id}-*.md"))
    parsed = parse_task_file(archived_file)
    assert parsed.subtasks[0].status == TaskStatus.DONE
    assert parsed.subtasks[1].status == TaskStatus.CANCELLED


def test_archive_force_already_closed_task(story_id: str) -> None:
    assert_invoke(app, ["done", "--force", story_id])
    result = assert_invoke(app, ["archive", "--force", story_id])
    assert "archived" in result.output


# --- JSON output ---


def test_json_archive_outputs_task_ref(story_id: str) -> None:
    assert_invoke(app, ["done", "--force", story_id])
    result = assert_invoke(app, ["--json-output", "archive", story_id])
    data = json.loads(result.output)
    assert "task_ref" in data
    assert story_id in data["task_ref"]


def test_json_archive_force_includes_forced_ids(story_id: str) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    result = assert_invoke(app, ["--json-output", "archive", "--force", story_id])
    data = json.loads(result.output)
    assert set(data["forced_task_ids"]) == {t01, t02}


def test_json_archive_not_closed_outputs_error(story_id: str) -> None:
    result = assert_invoke(
        app, ["--json-output", "archive", story_id], expect_error=True
    )
    data = json.loads(result.output)
    assert "error" in data


def test_archive_nonexistent_task_fails() -> None:
    assert_invoke(app, ["archive", "s99"], expect_error=True)


# --- new task ID must not collide with archived IDs ---


def test_new_task_skips_archived_ids(story_id: str) -> None:
    assert_invoke(app, ["done", "--force", story_id])
    assert_invoke(app, ["archive", story_id])

    # create a new task — its ID must be higher than the archived one
    new = create_task("Second story")
    assert new.task_id > story_id
