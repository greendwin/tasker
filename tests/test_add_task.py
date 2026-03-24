from pathlib import Path

import pytest

from tasker.base_types import TaskStatus
from tasker.main import app
from tasker.parse import parse_task_file

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
    task = parse_task_file(task_file)
    assert len(task.subtasks) == 2
    assert task.subtasks[0].id == f"{parent_id}t01"
    assert task.subtasks[0].title == "First subtask"
    assert task.subtasks[0].status == TaskStatus.PENDING
    assert task.subtasks[1].id == f"{parent_id}t02"
    assert task.subtasks[1].title == "Second subtask"


# --- adding subtask updates parent status ---


def test_add_subtask_to_done_parent_reopens_it(parent_id: str) -> None:
    assert_invoke(app, ["add", parent_id, "First subtask"])
    assert_invoke(app, ["done", f"{parent_id}t01"])
    # parent is now done; adding a new subtask should reopen it
    assert_invoke(app, ["add", parent_id, "Second subtask"])
    task_file = next(Path("planning").glob(f"{parent_id}-*.md"))
    task = parse_task_file(task_file)
    assert task.status == TaskStatus.PENDING


def test_add_subtask_to_cancelled_parent_reopens_it(parent_id: str) -> None:
    assert_invoke(app, ["add", parent_id, "First subtask"])
    assert_invoke(app, ["cancel", f"{parent_id}t01"])
    # parent is now cancelled; adding a new subtask should reopen it
    assert_invoke(app, ["add", parent_id, "Second subtask"])
    task_file = next(Path("planning").glob(f"{parent_id}-*.md"))
    task = parse_task_file(task_file)
    assert task.status == TaskStatus.PENDING


def test_add_subtask_to_in_progress_parent_keeps_status(parent_id: str) -> None:
    assert_invoke(app, ["add", parent_id, "First subtask"])
    assert_invoke(app, ["start", f"{parent_id}t01"])
    # parent is in-progress; adding another subtask keeps it in-progress
    assert_invoke(app, ["add", parent_id, "Second subtask"])
    task_file = next(Path("planning").glob(f"{parent_id}-*.md"))
    task = parse_task_file(task_file)
    assert task.status == TaskStatus.IN_PROGRESS


# --- add with --details ---


def test_add_detailed_subtask_upgrades_parent(parent_id: str) -> None:
    assert_invoke(
        app, ["add", parent_id, "Write CLI spec", "--details", "Cover all commands"]
    )
    # parent should be upgraded to extended (directory)
    parent_dir = next(Path("planning").glob(f"{parent_id}-*/"))
    assert parent_dir.is_dir()
    assert (parent_dir / "README.md").exists()


def test_add_detailed_subtask_creates_child_file(parent_id: str) -> None:
    assert_invoke(
        app, ["add", parent_id, "Write CLI spec", "--details", "Cover all commands"]
    )
    parent_dir = next(Path("planning").glob(f"{parent_id}-*/"))
    child_file = next(parent_dir.glob(f"{parent_id}t01-*.md"))
    assert child_file.exists()
    content = child_file.read_text()
    assert "Write CLI spec" in content
    assert "Cover all commands" in content


def test_add_detailed_subtask_removes_old_parent_file(parent_id: str) -> None:
    old_file = next(Path("planning").glob(f"{parent_id}-*.md"))
    assert old_file.exists()
    assert_invoke(
        app, ["add", parent_id, "Write CLI spec", "--details", "Cover all commands"]
    )
    assert not old_file.exists()


def test_add_detailed_subtask_output(parent_id: str) -> None:
    result = assert_invoke(
        app, ["add", parent_id, "Write CLI spec", "--details", "Cover all commands"]
    )
    assert f"{parent_id}t01" in result.output


def test_add_detailed_subtask_with_slug(parent_id: str) -> None:
    assert_invoke(
        app,
        [
            "add",
            parent_id,
            "Write CLI spec",
            "--details",
            "Cover all commands",
            "--slug",
            "cli-spec",
        ],
    )
    parent_dir = next(Path("planning").glob(f"{parent_id}-*/"))
    child_file = parent_dir / f"{parent_id}t01-cli-spec.md"
    assert child_file.exists()


def test_add_detailed_subtask_parent_readme_has_link(parent_id: str) -> None:
    assert_invoke(
        app, ["add", parent_id, "Write CLI spec", "--details", "Cover all commands"]
    )
    parent_dir = next(Path("planning").glob(f"{parent_id}-*/"))
    readme = (parent_dir / "README.md").read_text()
    assert f"[{parent_id}t01](" in readme


def test_add_inline_then_detailed_subtask(parent_id: str) -> None:
    assert_invoke(app, ["add", parent_id, "First inline"])
    assert_invoke(
        app, ["add", parent_id, "Second detailed", "--details", "Description"]
    )
    parent_dir = next(Path("planning").glob(f"{parent_id}-*/"))
    readme = (parent_dir / "README.md").read_text()
    # inline subtask rendered without link
    assert f"- [ ] {parent_id}t01: First inline" in readme
    # detailed subtask rendered with link
    assert f"[{parent_id}t02](" in readme


def test_add_detailed_subtask_child_parses_correctly(parent_id: str) -> None:
    assert_invoke(
        app, ["add", parent_id, "Write CLI spec", "--details", "Cover all commands"]
    )
    parent_dir = next(Path("planning").glob(f"{parent_id}-*/"))
    child_file = next(parent_dir.glob(f"{parent_id}t01-*.md"))
    child = parse_task_file(child_file)
    assert child.id == f"{parent_id}t01"
    assert child.title == "Write CLI spec"
    assert child.description == "Cover all commands"
    assert child.status == TaskStatus.PENDING
