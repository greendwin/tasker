from typer.testing import CliRunner

from tasker.cli import app
from tasker.exceptions import TaskerError

_runner = CliRunner()


def test_tasker_error_shows_clean_message() -> None:
    result = _runner.invoke(app, ["add", "s99", "Some task"])
    assert "Error:" in result.output
    assert result.exit_code != 0


def test_tasker_error_no_traceback_by_default() -> None:
    result = _runner.invoke(app, ["add", "s99", "Some task"])
    assert "Traceback" not in result.output


def test_debug_flag_propagates_exception() -> None:
    result = _runner.invoke(app, ["--debug", "add", "s99", "Some task"])
    assert isinstance(result.exception, TaskerError)


def test_debug_flag_does_not_print_clean_error() -> None:
    result = _runner.invoke(app, ["--debug", "add", "s99", "Some task"])
    assert "Error:" not in result.output
