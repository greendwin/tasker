import json
from pathlib import Path

import pytest

from tasker.cli import app
from tasker.parse import parse_task_file

from .conftest import GetTaskFile
from .helpers import add_subtask, assert_invoke, create_task

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def s1() -> str:
    return create_task("Story one").task_id


# ---------------------------------------------------------------------------
# Edit details (s14t01)
# ---------------------------------------------------------------------------


def test_edit_details_on_file_task(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A", details="Old details").task_id
    assert_invoke(app, ["edit", t01, "--details", "New details"])

    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    task_file = next(story_dir.glob(f"{t01}-*.md"))
    parsed = parse_task_file(task_file)
    assert parsed.task.description == "New details"


def test_edit_details_capitalizes_first_letter(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A", details="old details").task_id
    assert_invoke(app, ["edit", t01, "--details", "new description"])

    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    task_file = next(story_dir.glob(f"{t01}-*.md"))
    parsed = parse_task_file(task_file)
    assert parsed.task.description == "New description"


def test_edit_details_on_root_task(s1: str, get_task_file: GetTaskFile) -> None:
    assert_invoke(app, ["edit", s1, "--details", "Root description"])

    task_file = get_task_file(s1)
    parsed = parse_task_file(task_file)
    assert parsed.task.description == "Root description"


def test_edit_details_upgrades_inline_task(
    s1: str, tasks_root: Path, get_task_file: GetTaskFile
) -> None:
    t01 = add_subtask(s1, "Inline task").task_id

    # before: parent is a basic .md file (no directory)
    old_file = get_task_file(s1)
    assert old_file.is_file()

    assert_invoke(app, ["edit", t01, "--details", "Now has details"])

    # after: parent upgraded to extended (directory with README.md)
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    assert story_dir.is_dir()
    assert (story_dir / "README.md").exists()

    # child is now file-backed
    task_file = next(story_dir.glob(f"{t01}-*.md"))
    parsed = parse_task_file(task_file)
    assert parsed.task.description == "Now has details"


# ---------------------------------------------------------------------------
# Edit title (s14t02)
# ---------------------------------------------------------------------------


def test_edit_title(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Old title", details="Details").task_id
    assert_invoke(app, ["edit", t01, "--title", "new title"])

    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    task_file = next(story_dir.glob(f"{t01}-*.md"))
    parsed = parse_task_file(task_file)
    assert parsed.task.title == "New title"  # auto-capitalized


def test_edit_title_on_inline_task(s1: str, get_task_file: GetTaskFile) -> None:
    t01 = add_subtask(s1, "Old title").task_id
    assert_invoke(app, ["edit", t01, "--title", "updated title"])

    task_file = get_task_file(s1)
    content = task_file.read_text()
    assert "Updated title" in content


def test_edit_title_updates_parent_subtask_list(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Old title", details="Details").task_id
    assert_invoke(app, ["edit", t01, "--title", "brand new title"])

    # parent README should reference the new title
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    readme = story_dir / "README.md"
    content = readme.read_text()
    assert "Brand new title" in content


# ---------------------------------------------------------------------------
# Edit slug (s14t03)
# ---------------------------------------------------------------------------


def test_edit_slug(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A", details="Details").task_id
    assert_invoke(app, ["edit", t01, "--slug", "new-slug"])

    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    new_files = list(story_dir.glob(f"{t01}-new-slug.md"))
    assert len(new_files) == 1


def test_edit_slug_removes_old_file(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A", details="Details").task_id
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    old_file = next(story_dir.glob(f"{t01}-*.md"))
    old_path = old_file.resolve()

    assert_invoke(app, ["edit", t01, "--slug", "renamed"])
    assert not old_path.exists()


def test_edit_slug_upgrades_inline_task_and_parent(
    s1: str, tasks_root: Path, get_task_file: GetTaskFile
) -> None:
    t01 = add_subtask(s1, "Inline task").task_id

    # before: parent is a basic .md file
    old_file = get_task_file(s1)
    assert old_file.is_file()

    assert_invoke(app, ["edit", t01, "--slug", "custom-slug"])

    # after: parent upgraded to extended (directory with README.md)
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    assert story_dir.is_dir()
    assert (story_dir / "README.md").exists()

    # child is now file-backed with the custom slug
    task_file = next(story_dir.glob(f"{t01}-custom-slug.md"))
    assert task_file.exists()


# ---------------------------------------------------------------------------
# Multiple fields at once
# ---------------------------------------------------------------------------


def test_edit_multiple_fields(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A", details="Old details").task_id
    assert_invoke(
        app, ["edit", t01, "--title", "new title", "--details", "New details"]
    )

    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    task_file = next(story_dir.glob(f"{t01}-*.md"))
    parsed = parse_task_file(task_file)
    assert parsed.task.title == "New title"
    assert parsed.task.description == "New details"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_edit_no_flags_fails(s1: str) -> None:
    result = assert_invoke(app, ["edit", s1], expect_error=True)
    assert "at least one" in result.output.lower() or "error" in result.output.lower()


def test_edit_nonexistent_task_fails() -> None:
    assert_invoke(app, ["edit", "s99", "--title", "X"], expect_error=True)


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


def test_edit_json_output(s1: str) -> None:
    result = assert_invoke(app, ["--json-output", "edit", s1, "--title", "Updated"])
    data = json.loads(result.output)
    assert "task_ref" in data


def test_edit_json_error(s1: str) -> None:
    result = assert_invoke(app, ["--json-output", "edit", s1], expect_error=True)
    data = json.loads(result.output)
    assert "error" in data
