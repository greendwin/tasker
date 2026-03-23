from __future__ import annotations

from enum import Enum
from typing import Literal, TypeAlias

from pydantic import BaseModel

EXTENDED_TASK_FILENAME = "README.md"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    DONE = "done"


class TaskKind(str, Enum):
    INLINE = "inline"
    BASIC = "basic"
    EXTENDED = "extended"


class TaskBase(BaseModel):
    # any task has these fields
    id: str  # unique id that can be used to reference a task
    title: str  # short summary of a task
    status: TaskStatus
    parent: AnyTask | None


class FileTaskBase(TaskBase):
    slug: str

    # task data
    description: str | None = None
    subtasks: list[AnyTask]


class InlineTask(TaskBase):
    kind: Literal[TaskKind.INLINE] = TaskKind.INLINE


class BasicTask(FileTaskBase):
    kind: Literal[TaskKind.BASIC] = TaskKind.BASIC


class ExtendedTask(FileTaskBase):
    kind: Literal[TaskKind.EXTENDED] = TaskKind.EXTENDED


AnyTask: TypeAlias = InlineTask | BasicTask | ExtendedTask
