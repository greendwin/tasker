# Project

`tasker` is a simple file-based task tracker for git repositories. CLI built with `typer`, src layout under `src/tasker/`.

## Commands

```bash
# Run tests
poetry run tox -e test

# Lint (black check + isort check + mypy)
poetry run tox -e lint
```

## Development

* On any development iteration, the final step is to run `poetry run tox` (all environments). Always fix **all** reported issues.
* Never use `type: ignore` if it can be fixed normally.

## Architecture

Detailed design is described in `DESIGN.md`.

- `tests/helpers.py` — test helpers shared between all tests
- `tests/` — pytest tests using `assert_invoke` helper to invoke commands without a subprocess
- mypy is configured in strict mode for both `src/` and `tests/`
- tox environments: `lint` (black, isort, mypy, flake8) and `test` (pytest)
