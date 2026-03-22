from pathlib import Path

import pytest

from tasker.exceptions import TaskerError
from tasker.main import app
from tasker.task_repo import TaskRepo, generate_slug

from .helpers import assert_invoke, create_task


def make_repo() -> TaskRepo:
    planning = Path("planning")
    planning.mkdir(exist_ok=True)
    return TaskRepo(planning)


# --- next_child_id(None) → next story ID ---


def test_next_child_id_none_empty_dir() -> None:
    repo = make_repo()
    assert repo.next_child_id(None) == "s01"


def test_next_child_id_none_with_existing_stories() -> None:
    create_task("First story")
    create_task("Second story")
    repo = make_repo()
    assert repo.next_child_id(None) == "s03"


# --- next_child_id(task_ref) → next subtask ID ---


def test_next_child_id_story_no_subtasks() -> None:
    story_id = create_task("My story")
    repo = make_repo()
    assert repo.next_child_id(story_id) == f"{story_id}t01"


def test_next_child_id_story_with_subtasks() -> None:
    story_id = create_task("My story")
    assert_invoke(app, ["add", story_id, "First subtask"])
    assert_invoke(app, ["add", story_id, "Second subtask"])
    repo = make_repo()
    assert repo.next_child_id(story_id) == f"{story_id}t03"


def test_next_child_id_accepts_slug_ref() -> None:
    story_id = create_task("My story")
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    slug_ref = task_file.stem  # e.g. "s01-my-story"
    repo = make_repo()
    assert repo.next_child_id(slug_ref) == f"{story_id}t01"


def test_next_child_id_inline_task_raises() -> None:
    story_id = create_task("My story")
    assert_invoke(app, ["add", story_id, "Inline subtask"])
    inline_ref = f"{story_id}t01"
    repo = make_repo()
    with pytest.raises(TaskerError):
        repo.next_child_id(inline_ref)


def test_next_child_id_unknown_ref_raises() -> None:
    repo = make_repo()
    with pytest.raises(TaskerError):
        repo.next_child_id("s99")


# --- generate_slug ---


def test_generate_slug_basic() -> None:
    assert generate_slug("My story title") == "my-story-title"


def test_generate_slug_lowercases() -> None:
    assert generate_slug("UPPER CASE") == "upper-case"


def test_generate_slug_strips_special_chars() -> None:
    assert generate_slug("Hello, World!") == "hello-world"


def test_generate_slug_truncates_to_five_words() -> None:
    assert (
        generate_slug("one two three four five six seven") == "one-two-three-four-five"
    )


def test_generate_slug_preserves_numbers() -> None:
    assert generate_slug("Task 42 part 2") == "task-42-part-2"


def test_generate_slug_collapses_extra_spaces() -> None:
    assert generate_slug("too   many   spaces") == "too-many-spaces"
