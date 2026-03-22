from typing import Sequence

from click.testing import Result
from typer import Typer
from typer.testing import CliRunner

_runner = CliRunner()


def assert_invoke(
    app: Typer, args: Sequence[str], *, expect_error: bool = False
) -> Result:
    result = _runner.invoke(app, args)
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
