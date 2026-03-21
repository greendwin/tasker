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
tox -e test
pytest tests/ -v                        # directly, faster

# Lint (black check + isort check + mypy)
tox -e lint

# Format code
black src tests
isort src tests

# Type check
mypy src tests

# Run CLI
tasker --help
tasker hello
tasker hello Alice
```

## Architecture

- `src/tasker/main.py` — Typer app definition and all CLI commands; also the entry point (`tasker.main:app`)
- `tests/` — pytest tests using `typer.testing.CliRunner` to invoke commands without a subprocess
- mypy is configured in strict mode for both `src/` and `tests/`
- tox environments: `lint` (black, isort, mypy) and `test` (pytest)
