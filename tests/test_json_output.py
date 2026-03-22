import json
from typing import Any

from typer.testing import CliRunner

from tasker.main import app

_runner = CliRunner()


def _parse_json(output: str) -> Any:
    return json.loads(output.strip())


# --- success cases ---


def test_json_new_task_outputs_valid_json() -> None:
    result = _runner.invoke(app, ["--json-output", "new", "My task"])
    assert result.exit_code == 0
    _parse_json(result.output)  # must not raise


def test_json_new_task_is_single_object() -> None:
    result = _runner.invoke(app, ["--json-output", "new", "My task"])
    data = _parse_json(result.output)
    assert isinstance(data, dict)


def test_json_new_task_returns_task_id() -> None:
    result = _runner.invoke(app, ["--json-output", "new", "My task"])
    data = _parse_json(result.output)
    assert "task_id" in data


def test_json_new_task_id_is_correct() -> None:
    result = _runner.invoke(app, ["--json-output", "new", "My task"])
    data = _parse_json(result.output)
    assert data["task_id"] == "s01-my-task"


def test_json_new_task_no_extra_output() -> None:
    result = _runner.invoke(app, ["--json-output", "new", "My task"])
    # entire output must be parseable as a single JSON value
    _parse_json(result.output)
    assert "[green]" not in result.output
    assert "[blue]" not in result.output


def test_json_add_task_outputs_valid_json() -> None:
    _runner.invoke(app, ["new", "Parent story"])
    result = _runner.invoke(app, ["--json-output", "add", "s01", "Subtask"])
    assert result.exit_code == 0
    _parse_json(result.output)  # must not raise


def test_json_add_task_is_single_object() -> None:
    _runner.invoke(app, ["new", "Parent story"])
    result = _runner.invoke(app, ["--json-output", "add", "s01", "Subtask"])
    data = _parse_json(result.output)
    assert isinstance(data, dict)


def test_json_add_task_returns_task_id() -> None:
    _runner.invoke(app, ["new", "Parent story"])
    result = _runner.invoke(app, ["--json-output", "add", "s01", "Subtask"])
    data = _parse_json(result.output)
    assert "task_id" in data


def test_json_add_task_id_is_correct() -> None:
    _runner.invoke(app, ["new", "Parent story"])
    result = _runner.invoke(app, ["--json-output", "add", "s01", "Subtask"])
    data = _parse_json(result.output)
    assert data["task_id"] == "s01t01"


def test_json_add_task_no_extra_output() -> None:
    _runner.invoke(app, ["new", "Parent story"])
    result = _runner.invoke(app, ["--json-output", "add", "s01", "Subtask"])
    _parse_json(result.output)
    assert "[green]" not in result.output
    assert "[blue]" not in result.output


# --- error cases ---


def test_json_error_outputs_valid_json() -> None:
    result = _runner.invoke(app, ["--json-output", "add", "s99", "Task"])
    _parse_json(result.output)  # must not raise


def test_json_error_is_single_object() -> None:
    result = _runner.invoke(app, ["--json-output", "add", "s99", "Task"])
    data = _parse_json(result.output)
    assert isinstance(data, dict)


def test_json_error_contains_error_key() -> None:
    result = _runner.invoke(app, ["--json-output", "add", "s99", "Task"])
    data = _parse_json(result.output)
    assert "error" in data


def test_json_error_message_is_non_empty() -> None:
    result = _runner.invoke(app, ["--json-output", "add", "s99", "Task"])
    data = _parse_json(result.output)
    assert data["error"]


def test_json_error_exits_nonzero() -> None:
    result = _runner.invoke(app, ["--json-output", "add", "s99", "Task"])
    assert result.exit_code != 0


def test_json_error_no_plain_error_prefix() -> None:
    result = _runner.invoke(app, ["--json-output", "add", "s99", "Task"])
    assert "Error:" not in result.output


# --- debug + json ---


def test_json_debug_error_includes_traceback() -> None:
    result = _runner.invoke(app, ["--json-output", "--debug", "add", "s99", "Task"])
    data = _parse_json(result.output)
    assert "traceback" in data


def test_json_debug_error_traceback_non_empty() -> None:
    result = _runner.invoke(app, ["--json-output", "--debug", "add", "s99", "Task"])
    data = _parse_json(result.output)
    assert data["traceback"]


def test_json_no_debug_error_no_traceback() -> None:
    result = _runner.invoke(app, ["--json-output", "add", "s99", "Task"])
    data = _parse_json(result.output)
    assert "traceback" not in data


# --- task_ref in errors ---


def test_json_error_contains_task_ref() -> None:
    result = _runner.invoke(app, ["--json-output", "add", "s99", "Task"])
    data = _parse_json(result.output)
    assert "task_ref" in data


def test_json_error_task_ref_is_non_empty() -> None:
    result = _runner.invoke(app, ["--json-output", "add", "s99", "Task"])
    data = _parse_json(result.output)
    assert data["task_ref"]


def test_json_error_task_ref_contains_task_id() -> None:
    result = _runner.invoke(app, ["--json-output", "add", "s99", "Task"])
    data = _parse_json(result.output)
    assert "s99" in data["task_ref"]
