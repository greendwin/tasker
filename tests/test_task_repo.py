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


# --- _load_story ---


def test_load_story_raises_on_duplicate_id() -> None:
    story_id = create_task("My story")
    # create a second file with the same story ID but a different slug
    original = next(Path("planning").glob(f"{story_id}-*.md"))
    duplicate = original.parent / f"{story_id}-other-slug.md"
    duplicate.write_text(original.read_text())
    repo = make_repo()
    with pytest.raises(TaskerError, match="Ambiguous"):
        repo.resolve_ref(story_id)


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


# --- create_story ---


def test_create_story_returns_filename() -> None:
    repo = make_repo()
    filename = repo.create_story(
        title="My story", description=None, slug=None, extended=False
    )
    assert filename == "s01-my-story"


def test_create_story_capitalizes_title() -> None:
    repo = make_repo()
    repo.create_story(
        title="lowercase title", description=None, slug=None, extended=False
    )
    repo.flush_tasks_to_disk()
    content = next(Path("planning").glob("s01-*.md")).read_text()
    assert "Lowercase title" in content


def test_create_story_auto_slug() -> None:
    repo = make_repo()
    filename = repo.create_story(
        title="Amazing New Feature", description=None, slug=None, extended=False
    )
    assert "amazing-new-feature" in filename


def test_create_story_explicit_slug() -> None:
    repo = make_repo()
    filename = repo.create_story(
        title="My story", description=None, slug="custom-slug", extended=False
    )
    assert filename == "s01-custom-slug"


def test_create_story_no_disk_write_before_flush() -> None:
    repo = make_repo()
    repo.create_story(title="My story", description=None, slug=None, extended=False)
    assert not list(Path("planning").glob("s01-*.md"))


def test_create_story_writes_file_after_flush() -> None:
    repo = make_repo()
    repo.create_story(title="My story", description=None, slug=None, extended=False)
    repo.flush_tasks_to_disk()
    assert list(Path("planning").glob("s01-*.md"))


def test_create_story_increments_id_for_second_story() -> None:
    repo = make_repo()
    repo.create_story(title="First", description=None, slug=None, extended=False)
    repo.flush_tasks_to_disk()
    filename = repo.create_story(
        title="Second", description=None, slug=None, extended=False
    )
    assert filename.startswith("s02-")


# --- add_subtask (on repo) ---


def test_repo_add_subtask_returns_child_id() -> None:
    story_id = create_task("My story")
    repo = make_repo()
    child_id = repo.add_subtask(task_ref=story_id, title="Subtask one")
    assert child_id == f"{story_id}t01"


def test_repo_add_subtask_no_disk_write_before_flush() -> None:
    story_id = create_task("My story")
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    content_before = task_file.read_text()
    repo = make_repo()
    repo.add_subtask(task_ref=story_id, title="New subtask")
    assert task_file.read_text() == content_before


def test_repo_add_subtask_writes_after_flush() -> None:
    story_id = create_task("My story")
    repo = make_repo()
    child_id = repo.add_subtask(task_ref=story_id, title="New subtask")
    repo.flush_tasks_to_disk()
    content = next(Path("planning").glob(f"{story_id}-*.md")).read_text()
    assert child_id in content


def test_repo_add_subtask_inline_parent_raises() -> None:
    story_id = create_task("My story")
    assert_invoke(app, ["add", story_id, "First subtask"])
    repo = make_repo()
    with pytest.raises(NotImplementedError):
        repo.add_subtask(task_ref=f"{story_id}t01", title="Nested subtask")


# --- flush_tasks_to_disk ---


def test_flush_does_not_rewrite_unmodified_story() -> None:
    story_id = create_task("My story")
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    mtime_before = task_file.stat().st_mtime_ns
    repo = make_repo()
    repo.resolve_ref(story_id)  # load without modifying
    repo.flush_tasks_to_disk()
    assert task_file.stat().st_mtime_ns == mtime_before


def test_flush_rewrites_modified_story() -> None:
    story_id = create_task("My story")
    task_file = next(Path("planning").glob(f"{story_id}-*.md"))
    mtime_before = task_file.stat().st_mtime_ns
    repo = make_repo()
    repo.add_subtask(task_ref=story_id, title="New subtask")
    repo.flush_tasks_to_disk()
    assert task_file.stat().st_mtime_ns != mtime_before


def test_flush_twice_does_not_rewrite_unchanged() -> None:
    repo = make_repo()
    repo.create_story(title="My story", description=None, slug=None, extended=False)
    repo.flush_tasks_to_disk()
    task_file = next(Path("planning").glob("s01-*.md"))
    mtime_after_first_flush = task_file.stat().st_mtime_ns
    repo.flush_tasks_to_disk()
    assert task_file.stat().st_mtime_ns == mtime_after_first_flush
