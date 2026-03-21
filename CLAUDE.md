# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`tasker` is a simple file-based task tracker for git repositories. CLI built with `typer` + `typer_di`, src layout under `src/tasker/`.

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

## Architecture

- `src/tasker/main.py` — Typer app definition and all CLI commands; also the entry point (`tasker.main:app`)
- `tests/` — pytest tests using `typer.testing.CliRunner` to invoke commands without a subprocess
- mypy is configured in strict mode for both `src/` and `tests/`
- tox environments: `lint` (black, isort, mypy) and `test` (pytest)
