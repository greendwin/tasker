"""Tests for the hello command."""

from typer.testing import CliRunner

from tasker.main import app

runner = CliRunner()


def test_hello_no_name() -> None:
    result = runner.invoke(app, ["hello"])
    assert result.exit_code == 0
    assert "Hello, World!" in result.output


def test_hello_with_name() -> None:
    result = runner.invoke(app, ["hello", "Alice"])
    assert result.exit_code == 0
    assert "Hello, Alice!" in result.output
