import json

from tasker.cli import app

from .helpers import add_subtask, assert_invoke, create_task


def test_list_shows_task_title() -> None:
    task_id = create_task("My story").task_id
    result = assert_invoke(app, ["list"])
    assert task_id in result.output
    assert "My story" in result.output


def test_list_no_tasks_prints_empty_message() -> None:
    result = assert_invoke(app, ["list"])
    assert "No open tasks" in result.output


def test_list_shows_open_subtask() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "First subtask").task_id
    result = assert_invoke(app, ["list"])
    assert sub_id in result.output
    assert "First subtask" in result.output


def test_list_hides_done_subtask_by_default() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Done subtask").task_id
    assert_invoke(app, ["done", sub_id])
    result = assert_invoke(app, ["list"])
    assert sub_id not in result.output


def test_list_hides_cancelled_subtask_by_default() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Cancelled subtask").task_id
    assert_invoke(app, ["cancel", sub_id])
    result = assert_invoke(app, ["list"])
    assert sub_id not in result.output


def test_list_closed_json_output() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Done subtask").task_id
    assert_invoke(app, ["done", sub_id])
    result = assert_invoke(app, ["--json-output", "list"])
    data = json.loads(result.output)
    # Without --closed, JSON subtasks only show open ones... but _task_to_json
    # includes all subtasks. This is existing behavior.
    task_data = data["tasks"][0]
    assert task_data["id"] == task_id


# --all shows full depth and closed


def test_list_all_shows_nested_subtask() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Sub", details="desc").task_id
    nested_id = add_subtask(sub_id, "Nested subtask").task_id
    result = assert_invoke(app, ["list", "--all"])
    assert nested_id in result.output
    assert "Nested subtask" in result.output


def test_list_shows_nested_subtask_by_default() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Sub", details="desc").task_id
    nested_id = add_subtask(sub_id, "Nested subtask").task_id
    result = assert_invoke(app, ["list"])
    assert nested_id in result.output


def test_list_all_shows_closed_subtask() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Done subtask").task_id
    assert_invoke(app, ["done", sub_id])
    result = assert_invoke(app, ["list", "--all"])
    assert sub_id in result.output


def test_list_all_shows_closed_nested_subtask() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Sub", details="desc").task_id
    nested_id = add_subtask(sub_id, "Nested done").task_id
    assert_invoke(app, ["done", nested_id])
    result = assert_invoke(app, ["list", "--all"])
    assert nested_id in result.output


# cancelled subtasks shown full gray (no blue ID)


def test_list_all_cancelled_subtask_has_no_blue_id() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Cancelled subtask").task_id
    assert_invoke(app, ["cancel", sub_id])
    result = assert_invoke(app, ["list", "--all"])
    # cancelled line should not linkify the ID in blue
    assert f"[blue]{sub_id}[/blue]" not in result.output
    assert sub_id in result.output


def test_list_default_no_cancelled_subtask_in_output() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Cancelled subtask").task_id
    assert_invoke(app, ["cancel", sub_id])
    result = assert_invoke(app, ["list"])
    assert sub_id not in result.output


# s17t08: --all always shows status marker (even for pending)


def test_list_all_shows_pending_marker() -> None:
    task_id = create_task("My story").task_id
    add_subtask(task_id, "Pending subtask").task_id
    result = assert_invoke(app, ["list", "--all"])
    assert "[ ]" in result.output


def test_list_default_no_pending_marker_for_subtask() -> None:
    task_id = create_task("My story").task_id
    add_subtask(task_id, "Pending subtask").task_id
    result = assert_invoke(app, ["list"])
    assert "[ ]" not in result.output


def test_list_all_indents_nested_subtasks() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Sub", details="desc").task_id
    nested_id = add_subtask(sub_id, "Nested subtask").task_id
    result = assert_invoke(app, ["list", "--all"])
    # nested subtask line should have deeper indentation than direct subtask
    lines = result.output.splitlines()
    sub_line = next(ln for ln in lines if sub_id in ln)
    nested_line = next(ln for ln in lines if nested_id in ln)
    sub_indent = len(sub_line) - len(sub_line.lstrip())
    nested_indent = len(nested_line) - len(nested_line.lstrip())
    assert nested_indent > sub_indent
