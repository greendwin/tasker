# tasker

A simple file-based task tracker for git repositories.

## Installation

```bash
pip install tasker
```

Or with Poetry:

```bash
poetry install
```

## Usage

```bash
tasker hello
tasker hello Alice
```

## Development

```bash
poetry install --with dev

# Run tests
pytest tests/ -v

# Lint + type check
tox -e lint

# Format
black src tests
isort src tests
```

## Requirements

- Python >= 3.10
