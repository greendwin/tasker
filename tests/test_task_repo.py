from pathlib import Path

import pytest

from tasker.exceptions import TaskerError
from tasker.render import build_task_file_path
from tasker.repo import (
    TaskRepo,
    find_next_root_task_id,
    generate_slug,
    get_next_subtask_id,
)

from .helpers import add_subtask, create_task


def _tasker_root() -> Path:
    tasker_dir = Path("tasker")
    tasker_dir.mkdir(exist_ok=True)
    return tasker_dir


@pytest.fixture
def tasker_root() -> Path:
    return _tasker_root()


def make_repo() -> TaskRepo:
    return TaskRepo(_tasker_root())


# --- find_next_root_task_id → next story ID ---


def test_next_child_id_none_empty_dir() -> None:
    repo = make_repo()
    assert find_next_root_task_id(repo.loader) == "s01"


def test_next_child_id_none_with_existing_stories() -> None:
    create_task("First story")
    create_task("Second story")
    repo = make_repo()
    assert find_next_root_task_id(repo.loader) == "s03"


# --- get_next_subtask_id(task_ref) → next subtask ID ---


def test_next_child_id_story_no_subtasks() -> None:
    story_id = create_task("My story").task_id
    repo = make_repo()
    task = repo.resolve_ref(story_id)
    assert not task.is_inline
    assert get_next_subtask_id(task) == f"{story_id}t01"


def test_next_child_id_story_with_subtasks() -> None:
    story_id = create_task("My story").task_id
    add_subtask(story_id, "First subtask")
    add_subtask(story_id, "Second subtask")
    repo = make_repo()
    task = repo.resolve_ref(story_id)
    assert not task.is_inline
    assert get_next_subtask_id(task) == f"{story_id}t03"


def test_next_child_id_accepts_slug_ref() -> None:
    story_id = create_task("My story").task_id
    task_file = next(Path("tasker").glob(f"{story_id}-*.md"))
    slug_ref = task_file.stem  # e.g. "s01-my-story"
    repo = make_repo()
    task = repo.resolve_ref(slug_ref)
    assert not task.is_inline
    assert get_next_subtask_id(task) == f"{story_id}t01"


def test_add_subtask_upgrades_inline_parent() -> None:
    story_id = create_task("My story").task_id
    inline_id = add_subtask(story_id, "Inline subtask").task_id
    repo = make_repo()
    parent = repo.resolve_ref(inline_id)
    child = repo.add_subtask(parent, title="Nested subtask")
    assert parent.slug is not None
    assert not parent.is_inline
    assert child.id == f"{inline_id}01"


def test_next_child_id_unknown_ref_raises() -> None:
    repo = make_repo()
    with pytest.raises(TaskerError):
        repo.resolve_ref("s99")


# --- load_root_task ---


def test_load_story_raises_on_duplicate_id() -> None:
    story_id = create_task("My story").task_id
    # create a second file with the same story ID but a different slug
    original = next(Path("tasker").glob(f"{story_id}-*.md"))
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
    task = repo.create_root_task(
        title="My story", description=None, slug=None, extended=False
    )
    assert task.ref == "s01-my-story"


def test_create_story_capitalizes_title() -> None:
    repo = make_repo()
    repo.create_root_task(
        title="lowercase title", description=None, slug=None, extended=False
    )
    repo.flush_to_disk()
    content = next(Path("tasker").glob("s01-*.md")).read_text()
    assert "Lowercase title" in content


def test_create_story_auto_slug() -> None:
    repo = make_repo()
    task = repo.create_root_task(
        title="Amazing New Feature", description=None, slug=None, extended=False
    )
    assert "amazing-new-feature" in task.ref


def test_create_story_explicit_slug() -> None:
    repo = make_repo()
    task = repo.create_root_task(
        title="My story", description=None, slug="custom-slug", extended=False
    )
    assert task.ref == "s01-custom-slug"


def test_create_story_no_disk_write_before_flush() -> None:
    repo = make_repo()
    repo.create_root_task(title="My story", description=None, slug=None, extended=False)
    assert not list(Path("tasker").glob("s01-*.md"))


def test_create_story_writes_file_after_flush() -> None:
    repo = make_repo()
    repo.create_root_task(title="My story", description=None, slug=None, extended=False)
    repo.flush_to_disk()
    assert list(Path("tasker").glob("s01-*.md"))


def test_create_story_increments_id_for_second_story() -> None:
    repo = make_repo()
    repo.create_root_task(title="First", description=None, slug=None, extended=False)
    repo.flush_to_disk()
    task = repo.create_root_task(
        title="Second", description=None, slug=None, extended=False
    )
    assert task.ref.startswith("s02-")


# --- add_subtask (on repo) ---


def test_repo_add_subtask() -> None:
    story_id = create_task("My story").task_id
    repo = make_repo()
    parent = repo.resolve_ref(story_id)
    child = repo.add_subtask(parent, title="Subtask one")
    assert child.is_inline
    assert child.id == f"{story_id}t01"


def test_repo_add_subtask_no_disk_write_before_flush() -> None:
    story_id = create_task("My story").task_id
    task_file = next(Path("tasker").glob(f"{story_id}-*.md"))
    content_before = task_file.read_text()
    repo = make_repo()
    parent = repo.resolve_ref(story_id)
    repo.add_subtask(parent, title="New subtask")
    assert task_file.read_text() == content_before


def test_repo_add_subtask_writes_after_flush() -> None:
    story_id = create_task("My story").task_id
    repo = make_repo()
    parent = repo.resolve_ref(story_id)
    child = repo.add_subtask(parent, title="New subtask")
    repo.flush_to_disk()
    content = next(Path("tasker").glob(f"{story_id}-*.md")).read_text()
    assert child.id in content


def test_repo_add_subtask_upgrades_inline_parent() -> None:
    story_id = create_task("My story").task_id
    t01 = add_subtask(story_id, "First subtask").task_id
    repo = make_repo()
    parent = repo.resolve_ref(t01)
    child = repo.add_subtask(parent, title="Nested subtask")
    assert parent.slug == "first-subtask"
    assert child.title == "Nested subtask"
    repo.flush_to_disk()
    # parent should now be file-backed in parent's extended dir
    story_dir = next(Path("tasker").glob(f"{story_id}-*/"))
    assert (story_dir / f"{t01}-first-subtask.md").exists()


# --- flush_tasks_to_disk ---


def test_flush_does_not_rewrite_unmodified_story() -> None:
    story_id = create_task("My story").task_id
    task_file = next(Path("tasker").glob(f"{story_id}-*.md"))
    mtime_before = task_file.stat().st_mtime_ns
    repo = make_repo()
    repo.resolve_ref(story_id)  # load without modifying
    repo.flush_to_disk()
    assert task_file.stat().st_mtime_ns == mtime_before


def test_flush_rewrites_modified_story() -> None:
    story_id = create_task("My story").task_id
    task_file = next(Path("tasker").glob(f"{story_id}-*.md"))
    mtime_before = task_file.stat().st_mtime_ns
    repo = make_repo()
    parent = repo.resolve_ref(story_id)
    repo.add_subtask(parent, title="New subtask")
    repo.flush_to_disk()
    assert task_file.stat().st_mtime_ns != mtime_before


def test_flush_twice_does_not_rewrite_unchanged() -> None:
    repo = make_repo()
    repo.create_root_task(title="My story", description=None, slug=None, extended=False)
    repo.flush_to_disk()
    task_file = next(Path("tasker").glob("s01-*.md"))
    mtime_after_first_flush = task_file.stat().st_mtime_ns
    repo.flush_to_disk()
    assert task_file.stat().st_mtime_ns == mtime_after_first_flush


def test_dont_reset_nested_tasks(tasker_root: Path) -> None:
    story_ref = create_task("Story").task_ref
    task_ref = add_subtask(story_ref, "Task", details="File-based task").task_ref
    subtask_ref = add_subtask(task_ref, "Subtask").task_ref

    task_path = tasker_root / story_ref / f"{task_ref}.md"
    assert task_path.exists()
    assert subtask_ref in task_path.read_text()

    # load and resave story
    repo = TaskRepo(tasker_root)
    _ = repo.resolve_ref(story_ref)
    repo.flush_to_disk()

    # ensure that subtask still exists
    assert task_path.exists()
    assert subtask_ref in task_path.read_text()


# --- task statuses ---


def test_flush_upgrades_basic_to_extended() -> None:
    """When extended flag changes, flush removes old .md and creates dir/README.md."""
    repo = make_repo()
    task = repo.create_root_task(
        title="My story", description=None, slug=None, extended=False
    )
    repo.flush_to_disk()

    old_path = Path("tasker") / f"{task.ref}.md"
    assert old_path.exists()

    # Simulate upgrade: set extended flag
    task.extended = True
    repo.flush_to_disk()

    # Old .md file should be removed
    assert not old_path.exists()
    # New directory structure should exist
    new_path = Path("tasker") / task.ref / "README.md"
    assert new_path.exists()


def test_flush_upgrade_preserves_content() -> None:
    """Content is preserved when upgrading from basic to extended."""
    repo = make_repo()
    task = repo.create_root_task(
        title="My story", description="Some details", slug=None, extended=False
    )
    repo.flush_to_disk()

    old_path = Path("tasker") / f"{task.ref}.md"
    old_content = old_path.read_text()

    task.extended = True
    repo.flush_to_disk()

    new_path = Path("tasker") / task.ref / "README.md"
    new_content = new_path.read_text()
    assert new_content == old_content


def test_update_statuses_on_load() -> None:
    repo = make_repo()
    task = repo.create_root_task(
        title="My story", description=None, slug=None, extended=False
    )
    repo.add_subtask(task, title="Subtask")
    repo.flush_to_disk()

    # custom edit and mark subtask done
    task_path = build_task_file_path(repo.root, task.ref, task.extended)
    patched_content = task_path.read_text().replace("[ ]", "[x]")
    task_path.write_text(patched_content)

    # sanity check
    assert "status: pending" in patched_content

    # recreate repo
    repo = make_repo()

    # resave loaded data
    _ = repo.resolve_ref(task.ref)
    repo.flush_to_disk()

    # task must be updated automagically
    updated_content = task_path.read_text()
    assert "status: done" in updated_content
