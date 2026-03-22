# Project

`tasker` is a simple file-based task tracker for git repositories. CLI built with `typer`, src layout under `src/tasker/`.

## Setup

```bash
poetry install --with dev
```

## Commands

```bash
# Run tests
poetry run tox -e test
poetry run pytest tests/ -v             # directly, faster

# Lint (black check + isort check + mypy)
poetry run tox -e lint

# Format code
poetry run black src tests
poetry run isort src tests

# Type check
poetry run mypy src tests
```

## Development

On any development iteration, the final step is to run `poetry run tox` (all environments). Always fix **all** reported issues.

## Architecture

Detailed design is described in `DESIGN.md`.

- `src/tasker/main.py` — Typer app definition and all CLI commands; also the entry point (`tasker.main:app`)
- `src/tasker/task/` — task domain: types (`_base_types.py`), parser (`_parse_task.py`), renderer (`_render_task.py`)
- `src/tasker/utils.py` — shared `rich` console instance
- `tests/helpers.py` — test helpers shared between all tests
- `tests/` — pytest tests using `assert_invoke` helper to invoke commands without a subprocess
- mypy is configured in strict mode for both `src/` and `tests/`
- tox environments: `lint` (black, isort, mypy, flake8) and `test` (pytest)
