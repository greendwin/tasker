from pathlib import Path

from ._exceptions import TaskerError
from .task import EXTENDED_TASK_FILENAME


def find_task_file(root: Path, task_id: str) -> Path:
    candidates = [
        p
        for p in root.rglob(f"{task_id}-*")
        if p.is_dir() or (p.suffix == ".md" and p.name != EXTENDED_TASK_FILENAME)
    ]
    if not candidates:
        raise TaskerError(f"Task {task_id!r} not found", task_ref=task_id)

    dirs = [p for p in candidates if p.is_dir()]
    return dirs[0] if dirs else candidates[0]
