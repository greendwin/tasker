import pytest

from tasker.exceptions import TaskValidateError
from tasker.parse import ParsedRef, parse_task_ref


def test_root_story_id_only() -> None:
    result = parse_task_ref("s01")
    assert result == ParsedRef(task_id="s01", parent_id="s01", root_id="s01", slug=None)


def test_root_story_with_slug() -> None:
    result = parse_task_ref("s01-my-story")
    assert result == ParsedRef(
        task_id="s01", parent_id="s01", root_id="s01", slug="my-story"
    )


def test_direct_subtask_id_only() -> None:
    result = parse_task_ref("s01t01")
    assert result == ParsedRef(
        task_id="s01t01", parent_id="s01", root_id="s01", slug=None
    )


def test_direct_subtask_with_slug() -> None:
    result = parse_task_ref("s01t01-define-task-forms")
    assert result == ParsedRef(
        task_id="s01t01", parent_id="s01", root_id="s01", slug="define-task-forms"
    )


def test_nested_subtask() -> None:
    result = parse_task_ref("s01t0102")
    assert result == ParsedRef(
        task_id="s01t0102", parent_id="s01t01", root_id="s01", slug=None
    )


def test_deeply_nested_subtask() -> None:
    result = parse_task_ref("s01t010203")
    assert result == ParsedRef(
        task_id="s01t010203", parent_id="s01t0102", root_id="s01", slug=None
    )


def test_multi_digit_story_number() -> None:
    result = parse_task_ref("s123t01")
    assert result == ParsedRef(
        task_id="s123t01", parent_id="s123", root_id="s123", slug=None
    )


def test_invalid_ref_raises() -> None:
    with pytest.raises(TaskValidateError, match="Invalid task ref"):
        parse_task_ref("invalid")


def test_empty_ref_raises() -> None:
    with pytest.raises(TaskValidateError, match="Invalid task ref"):
        parse_task_ref("")


def test_partial_subtask_id_raises() -> None:
    # "t" alone without a digit group is not valid
    with pytest.raises(TaskValidateError, match="Invalid task ref"):
        parse_task_ref("t01")
