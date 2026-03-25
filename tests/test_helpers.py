import pytest

from tasker.cli import app

from .helpers import assert_invoke


def test_assert_invoke_returns_result_on_success() -> None:
    result = assert_invoke(app, ["new", "some title"])
    assert result.exit_code == 0


def test_assert_invoke_raises_on_nonzero_exit() -> None:
    with pytest.raises(AssertionError):
        assert_invoke(app, ["new"])  # missing required argument → exit code 2


def test_assert_invoke_error_includes_exit_code() -> None:
    with pytest.raises(AssertionError, match="code 2"):
        assert_invoke(app, ["new"])


def test_assert_invoke_error_includes_output() -> None:
    with pytest.raises(AssertionError, match="Missing argument"):
        assert_invoke(app, ["new"])


def test_assert_invoke_expect_error_passes_on_nonzero_exit() -> None:
    result = assert_invoke(app, ["new"], expect_error=True)
    assert result.exit_code != 0


def test_assert_invoke_expect_error_raises_on_success() -> None:
    with pytest.raises(AssertionError):
        assert_invoke(app, ["new", "some title"], expect_error=True)


def test_assert_invoke_expect_error_message_includes_output() -> None:
    with pytest.raises(AssertionError, match="expected to fail"):
        assert_invoke(app, ["new", "some title"], expect_error=True)
