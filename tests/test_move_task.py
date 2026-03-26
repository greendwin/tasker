import json
from pathlib import Path

import pytest

from tasker.cli import app
from tasker.parse import parse_task_file

from .helpers import add_subtask, assert_invoke, create_task

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def s1() -> str:
    return create_task("Story one").task_id


@pytest.fixture()
def s2() -> str:
    return create_task("Story two").task_id


# ---------------------------------------------------------------------------
# move --parent : basic cases
# ---------------------------------------------------------------------------


def test_move_inline_subtask_to_another_parent(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    result = assert_invoke(app, ["move", t01, "--parent", s2])
    assert "moved" in result.output
    assert s2 in result.output


def test_move_file_subtask_to_another_parent(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task A", details="Has details").task_id
    result = assert_invoke(app, ["move", t01, "--parent", s2])
    assert "moved" in result.output


def test_move_root_task_under_another(s1: str, s2: str) -> None:
    result = assert_invoke(app, ["move", s1, "--parent", s2])
    assert "moved" in result.output
    assert s2 in result.output


def test_move_extended_subtask_to_another_parent(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Parent task", details="Details").task_id
    add_subtask(t01, "Child", details="Nested details")
    result = assert_invoke(app, ["move", t01, "--parent", s2])
    assert "moved" in result.output


# ---------------------------------------------------------------------------
# move --root
# ---------------------------------------------------------------------------


def test_move_subtask_to_root(s1: str) -> None:
    t01 = add_subtask(s1, "Promote me").task_id
    result = assert_invoke(app, ["move", t01, "--root"])
    assert "moved" in result.output
    assert "root" in result.output


def test_move_file_subtask_to_root(s1: str) -> None:
    t01 = add_subtask(s1, "Promote me", details="Has content").task_id
    result = assert_invoke(app, ["move", t01, "--root"])
    assert "root" in result.output


def test_move_extended_subtask_to_root(s1: str) -> None:
    t01 = add_subtask(s1, "Container", details="Details").task_id
    add_subtask(t01, "Child A")
    add_subtask(t01, "Child B")
    result = assert_invoke(app, ["move", t01, "--root"])
    assert "root" in result.output


# ---------------------------------------------------------------------------
# ID recalculation (s09t03)
# ---------------------------------------------------------------------------


def test_renames_are_printed(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task").task_id
    result = assert_invoke(app, ["move", t01, "--parent", s2])
    # The old id and new id should both appear (renamed)
    assert t01 in result.output
    # new id is s2 + tNN
    assert f"{s2}t01" in result.output


def test_renames_deep_subtree(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Level 1", details="D").task_id
    t0101 = add_subtask(t01, "Level 2").task_id
    result = assert_invoke(app, ["move", t01, "--parent", s2])
    assert t01 in result.output
    assert t0101 in result.output


def test_json_renames(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task").task_id
    result = assert_invoke(app, ["--json-output", "move", t01, "--parent", s2])
    data = json.loads(result.output)
    assert "renames" in data
    assert data["renames"][0]["old_id"] == t01
    assert "task_ref" in data


def test_json_move_to_root(s1: str) -> None:
    t01 = add_subtask(s1, "Task").task_id
    result = assert_invoke(app, ["--json-output", "move", t01, "--root"])
    data = json.loads(result.output)
    assert "renames" in data
    assert "task_ref" in data


# ---------------------------------------------------------------------------
# File cleanup (s09t04)
# ---------------------------------------------------------------------------


def test_old_basic_file_removed_after_move(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task A", details="Details").task_id
    # find original file
    story_dir = next(Path("tasker").glob(f"{s1}-*/"))
    old_file = next(story_dir.glob(f"{t01}-*.md"))
    assert old_file.exists()

    assert_invoke(app, ["move", t01, "--parent", s2])
    assert not old_file.exists()


def test_old_extended_dir_removed_after_move(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Container", details="Details").task_id
    add_subtask(t01, "Child", details="Child details")
    story_dir = next(Path("tasker").glob(f"{s1}-*/"))
    old_dir = next(story_dir.glob(f"{t01}-*/"))
    assert old_dir.is_dir()

    assert_invoke(app, ["move", t01, "--parent", s2])
    assert not old_dir.exists()


def test_old_extended_dir_with_user_data_not_removed(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Container", details="Details").task_id
    add_subtask(t01, "Child", details="Child details")
    story_dir = next(Path("tasker").glob(f"{s1}-*/"))
    old_dir = next(story_dir.glob(f"{t01}-*/"))

    # place a non-task file inside the extended directory
    user_file = old_dir / "notes.txt"
    user_file.write_text("user notes")

    result = assert_invoke(app, ["move", t01, "--parent", s2], expect_error=True)
    assert "non-task files" in result.output

    # user data must still be there
    assert user_file.exists()
    assert user_file.read_text() == "user notes"


def test_new_file_created_after_move(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task A", details="Details").task_id
    assert_invoke(app, ["move", t01, "--parent", s2])
    # new file should be under s2's directory
    story_dir = next(Path("tasker").glob(f"{s2}-*/"))
    new_files = list(story_dir.glob(f"{s2}t01-*.md"))
    assert len(new_files) == 1


def test_old_root_file_removed_when_moved_under_parent(s1: str, s2: str) -> None:
    old_file = next(Path("tasker").glob(f"{s1}-*.md"))
    assert old_file.exists()

    assert_invoke(app, ["move", s1, "--parent", s2])
    assert not old_file.exists()


def test_move_to_root_creates_root_file(s1: str) -> None:
    t01 = add_subtask(s1, "Promote me", details="Content").task_id
    assert_invoke(app, ["move", t01, "--root"])
    # should be a new root task file
    # new root ID should be s03 or higher (s1=s01, s2 not created here but
    # we only have s1 in this test)
    new_files = list(Path("tasker").glob("s*-promote-me.md"))
    assert len(new_files) == 1


# ---------------------------------------------------------------------------
# Parent subtask list updated
# ---------------------------------------------------------------------------


def test_old_parent_subtask_list_updated(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Mover").task_id
    add_subtask(s1, "Stayer")
    assert_invoke(app, ["move", t01, "--parent", s2])

    # old parent should only have "Stayer"
    story_file = next(Path("tasker").glob(f"{s1}-*.md"))
    content = story_file.read_text()
    assert "Mover" not in content
    assert "Stayer" in content


def test_new_parent_subtask_list_updated(s1: str, s2: str) -> None:
    add_subtask(s1, "Task A")
    assert_invoke(app, ["move", f"{s1}t01", "--parent", s2])

    # new parent should list the moved task (may be .md or dir/README.md)
    candidates = list(Path("tasker").glob(f"{s2}-*"))
    assert len(candidates) == 1
    path = candidates[0]
    content = (path / "README.md").read_text() if path.is_dir() else path.read_text()
    assert f"{s2}t01" in content
    assert "Task A" in content


# ---------------------------------------------------------------------------
# Task content preserved after move
# ---------------------------------------------------------------------------


def test_moved_task_preserves_description(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Described task", details="Important details").task_id
    assert_invoke(app, ["move", t01, "--parent", s2])
    story_dir = next(Path("tasker").glob(f"{s2}-*/"))
    new_file = next(story_dir.glob(f"{s2}t01-*.md"))
    parsed = parse_task_file(new_file)
    assert parsed.task.description == "Important details"


def test_moved_task_preserves_status(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Started task").task_id
    assert_invoke(app, ["start", t01])
    assert_invoke(app, ["move", t01, "--parent", s2])
    # parent may have been upgraded to extended (directory)
    candidates = list(Path("tasker").glob(f"{s2}-*"))
    path = candidates[0]
    content = (path / "README.md").read_text() if path.is_dir() else path.read_text()
    assert "[~]" in content  # in-progress checkbox


def test_moved_task_preserves_inline_subtasks(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Container", details="Details").task_id
    add_subtask(t01, "Child A")
    add_subtask(t01, "Child B")
    assert_invoke(app, ["move", t01, "--parent", s2])

    # s2 is now extended (directory) because it gained a file-backed subtask
    story_dir = next(Path("tasker").glob(f"{s2}-*/"))
    assert story_dir.is_dir()
    # container is basic (inline subtasks only) — a .md file
    container_file = next(story_dir.glob(f"{s2}t01-*.md"))
    content = container_file.read_text()
    assert "Child A" in content
    assert "Child B" in content


def test_moved_extended_task_preserves_file_subtasks(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Container", details="Details").task_id
    add_subtask(t01, "Child A", details="A details")
    add_subtask(t01, "Child B", details="B details")
    assert_invoke(app, ["move", t01, "--parent", s2])

    story_dir = next(Path("tasker").glob(f"{s2}-*/"))
    container_dir = next(story_dir.glob(f"{s2}t01-*/"))
    assert container_dir.is_dir()
    readme = container_dir / "README.md"
    assert readme.exists()
    content = readme.read_text()
    assert "Child A" in content
    assert "Child B" in content


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


def test_move_requires_flag(s1: str) -> None:
    t01 = add_subtask(s1, "Task").task_id
    result = assert_invoke(app, ["move", t01], expect_error=True)
    assert "--parent" in result.output or "--root" in result.output


def test_move_rejects_both_flags(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task").task_id
    result = assert_invoke(
        app, ["move", t01, "--parent", s2, "--root"], expect_error=True
    )
    assert "both" in result.output.lower()


def test_move_root_to_root_is_idempotent(s1: str) -> None:
    result = assert_invoke(app, ["move", s1, "--root"])
    assert "already" in result.output.lower()


def test_move_under_self_fails(s1: str) -> None:
    result = assert_invoke(app, ["move", s1, "--parent", s1], expect_error=True)
    assert "itself" in result.output.lower()


def test_move_under_descendant_fails(s1: str) -> None:
    t01 = add_subtask(s1, "Child", details="Details").task_id
    result = assert_invoke(app, ["move", s1, "--parent", t01], expect_error=True)
    assert "descendant" in result.output.lower()


def test_move_to_same_parent_is_idempotent(s1: str) -> None:
    t01 = add_subtask(s1, "Child").task_id
    result = assert_invoke(app, ["move", t01, "--parent", s1])
    assert "already" in result.output.lower()


def test_move_nonexistent_task_fails() -> None:
    assert_invoke(app, ["move", "s99", "--root"], expect_error=True)


def test_move_nonexistent_parent_fails(s1: str) -> None:
    t01 = add_subtask(s1, "Task").task_id
    assert_invoke(app, ["move", t01, "--parent", "s99"], expect_error=True)


# ---------------------------------------------------------------------------
# JSON output for errors
# ---------------------------------------------------------------------------


def test_json_move_error(s1: str) -> None:
    result = assert_invoke(
        app, ["--json-output", "move", s1, "--parent", s1], expect_error=True
    )
    data = json.loads(result.output)
    assert "error" in data


def test_json_move_idempotent(s1: str) -> None:
    result = assert_invoke(app, ["--json-output", "move", s1, "--root"])
    data = json.loads(result.output)
    assert data.get("already") is True
    assert "task_ref" in data
