from pathlib import Path

from typer.testing import CliRunner

from tasker.main import app

runner = CliRunner()


def test_add_simple_task() -> None:
    result = runner.invoke(app, ["add", "Simple task summary"])
    assert result.exit_code == 0
    assert "task s01-simple-task-summary created" in result.output
    assert Path("planning/s01-simple-task-summary.md").exists()


def test_task_continious_numbering() -> None:
    result = runner.invoke(app, ["add", "first task"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["add", "second task"])
    assert result.exit_code == 0
    assert "task s02-second-task created" in result.output
    assert Path("planning/s02-second-task.md").exists()


def test_add_task_file_contains_title() -> None:
    runner.invoke(app, ["add", "My important task"])
    content = Path("planning/s01-my-important-task.md").read_text()
    assert "My important task" in content


def test_add_task_file_contains_pending_status() -> None:
    runner.invoke(app, ["add", "My important task"])
    content = Path("planning/s01-my-important-task.md").read_text()
    assert "Status: pending" in content
