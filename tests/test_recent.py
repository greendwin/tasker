from pathlib import Path

import pytest

from tasker.cli import app

from .helpers import add_subtask, assert_invoke, create_task


def _read_recent(tasks_root: Path) -> str | None:
    path = tasks_root / ".recent"
    if not path.exists():
        return None
    text = path.read_text().strip()
    return text or None


@pytest.fixture()
def s1() -> str:
    return create_task("Story one").task_id


# ---------------------------------------------------------------------------
# Store last target task on commands
# ---------------------------------------------------------------------------


def test_new_stores_recent(tasks_root: Path) -> None:
    ref = create_task("Brand new story")
    assert _read_recent(tasks_root) == ref.task_id


def test_add_stores_recent(s1: str, tasks_root: Path) -> None:
    add_subtask(s1, "Child task")
    assert _read_recent(tasks_root) == s1


def test_edit_stores_recent(s1: str, tasks_root: Path) -> None:
    assert_invoke(app, ["edit", s1, "--title", "Updated title"])
    assert _read_recent(tasks_root) == s1


def test_move_stores_recent(tasks_root: Path) -> None:
    s1 = create_task("Story A").task_id
    s2 = create_task("Story B").task_id
    t01 = add_subtask(s1, "Task to move", details="d").task_id

    assert_invoke(app, ["move", t01, "--parent", s2])
    # after move, task ID changes (s01t01 -> s02t01)
    recent = _read_recent(tasks_root)
    assert recent is not None
    assert recent.startswith(s2)


def test_unarchive_stores_recent(tasks_root: Path) -> None:
    s1 = create_task("Archivable story").task_id
    assert_invoke(app, ["done", s1])
    assert_invoke(app, ["archive", s1])

    assert_invoke(app, ["unarchive", s1])
    assert _read_recent(tasks_root) == s1


def test_start_stores_recent(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    assert_invoke(app, ["start", t01])
    assert _read_recent(tasks_root) == t01


def test_done_stores_recent(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    assert_invoke(app, ["done", t01])
    assert _read_recent(tasks_root) == t01


def test_cancel_stores_recent(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    assert_invoke(app, ["cancel", t01])
    assert _read_recent(tasks_root) == t01


def test_reset_stores_recent(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    assert_invoke(app, ["start", t01])
    assert_invoke(app, ["reset", t01])
    assert _read_recent(tasks_root) == t01


# ---------------------------------------------------------------------------
# .recent file and .gitignore
# ---------------------------------------------------------------------------


def test_recent_written_to_file(tasks_root: Path) -> None:
    ref = create_task("Test story")
    recent_file = tasks_root / ".recent"
    assert recent_file.exists()
    assert recent_file.read_text().strip() == ref.task_id


def test_gitignore_created(tasks_root: Path) -> None:
    create_task("Test story")
    gitignore = tasks_root / ".gitignore"
    assert gitignore.exists()
    lines = gitignore.read_text().splitlines()
    assert ".recent" in lines
    assert ".gitignore" in lines


def test_gitignore_not_duplicated(tasks_root: Path) -> None:
    create_task("Story one")
    create_task("Story two")

    gitignore = tasks_root / ".gitignore"
    lines = [ln for ln in gitignore.read_text().splitlines() if ln == ".recent"]
    assert len(lines) == 1


def test_gitignore_does_not_add_itself_when_preexisting(tasks_root: Path) -> None:
    gitignore = tasks_root / ".gitignore"
    gitignore.write_text("*.tmp\n")

    create_task("Story")

    lines = gitignore.read_text().splitlines()
    assert ".gitignore" not in lines


def test_gitignore_preserves_existing_content(tasks_root: Path) -> None:
    gitignore = tasks_root / ".gitignore"
    gitignore.write_text("*.tmp\n")

    create_task("Story")

    content = gitignore.read_text()
    assert "*.tmp" in content
    assert ".recent" in content.splitlines()


def test_load_recent_returns_none_when_no_file(tasks_root: Path) -> None:
    assert _read_recent(tasks_root) is None


# ---------------------------------------------------------------------------
# Resolve 'q' reference
# ---------------------------------------------------------------------------


def test_q_resolves_to_recent_task(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    assert_invoke(app, ["start", t01])  # sets recent to t01

    # 'q' should resolve to t01 — use edit which requires valid task ref
    assert_invoke(app, ["edit", "q", "--title", "Updated via q"])


def test_q_errors_when_no_recent(tasks_root: Path) -> None:
    assert_invoke(app, ["edit", "q", "--title", "nope"], expect_error=True)


def test_q_does_not_update_recent(s1: str, tasks_root: Path) -> None:
    add_subtask(s1, "Task A")
    t02 = add_subtask(s1, "Task B").task_id
    assert_invoke(app, ["start", t02])  # sets recent to t02

    # 'q' is not a direct link — recent should stay as t02
    assert_invoke(app, ["edit", "q", "--title", "Edited via q"])
    assert _read_recent(tasks_root) == t02


# ---------------------------------------------------------------------------
# Resolve 'p' reference
# ---------------------------------------------------------------------------


def test_p_resolves_to_parent_of_recent(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    assert_invoke(app, ["start", t01])  # recent = s01t01

    # 'p' should resolve to s01 (parent of s01t01)
    assert_invoke(app, ["edit", "p", "--title", "Parent edited via p"])


def test_p_resolves_to_parent_of_nested_task(tasks_root: Path) -> None:
    s1 = create_task("Story one").task_id
    t01 = add_subtask(s1, "Task A", details="d").task_id
    t0101 = add_subtask(t01, "Subtask A1").task_id
    assert_invoke(app, ["start", t0101])  # recent = s01t0101

    # 'p' should resolve to s01t01 (parent of s01t0101)
    assert_invoke(app, ["edit", "p", "--title", "Mid-level edited via p"])


def test_p_on_root_task_resolves_to_itself(tasks_root: Path) -> None:
    s1 = create_task("Story one").task_id
    assert_invoke(app, ["edit", s1, "--title", "Set recent"])  # recent = s01

    # 'p' of root task is the root task itself
    assert_invoke(app, ["edit", "p", "--title", "Root edited via p"])


def test_p_errors_when_no_recent(tasks_root: Path) -> None:
    assert_invoke(app, ["edit", "p", "--title", "nope"], expect_error=True)


def test_p_updates_recent_to_parent(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    assert_invoke(app, ["start", t01])  # recent = s01t01

    # 'p' resolves to s01, which is a direct ref — so recent is updated to s01
    assert_invoke(app, ["edit", "p", "--title", "Parent edited via p"])
    assert _read_recent(tasks_root) == s1
