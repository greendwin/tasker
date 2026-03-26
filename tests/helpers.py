import json
from typing import Sequence

from click.testing import Result
from typer import Typer
from typer.testing import CliRunner

from tasker.cli import app
from tasker.parse import ParsedRef, parse_task_ref

_runner = CliRunner()


def assert_invoke(
    app: Typer,
    args: Sequence[str],
    *,
    expect_error: bool = False,
    input: str | None = None,
) -> Result:
    result = _runner.invoke(app, args, input=input, catch_exceptions=False)
    if expect_error:
        if result.exit_code == 0:
            raise AssertionError(
                f"Command was expected to fail but exited with code 0:\n{result.output}"
            )
    elif result.exit_code != 0:
        raise AssertionError(
            f"Command exited with code {result.exit_code}:\n{result.output}"
        )
    return result


def create_task(title: str) -> ParsedRef:
    result = assert_invoke(app, ["--json-output", "new", title])
    task_ref = json.loads(result.output.strip())["task_ref"]
    return parse_task_ref(task_ref)


def add_subtask(parent_ref: str, title: str, details: str | None = None) -> ParsedRef:
    args = ["--json-output", "add", parent_ref, title]
    if details is not None:
        args.extend(["--details", details])

    result = assert_invoke(app, args)
    task_ref = json.loads(result.output.strip())["task_ref"]
    return parse_task_ref(task_ref)
