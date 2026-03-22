__all__ = [
    "TaskStatus",
    "Task",
]

from enum import Enum

from pydantic import BaseModel


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    DONE = "done"


class Task(BaseModel):
    id: str
    slug: str
    title: str
    description: str | None = None
    status: TaskStatus
    subtasks: list["Task"]

    # format info
    detailed: bool = False  # whether task is in form of directory
    loaded: bool  # whether task is fully loaded (in case of task as separate file)
    filename: str | None  # None in case of simple bullet list
