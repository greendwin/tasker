from __future__ import annotations

from enum import Enum
from typing import Literal, TypeAlias

from pydantic import BaseModel
from typing_extensions import override

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

    @property
    def ref(self) -> str:
        return self.id


class FileTaskBase(TaskBase):
    slug: str

    # task data
    description: str | None = None
    subtasks: list[AnyTask]

    @property
    @override
    def ref(self) -> str:
        return build_task_ref(self.id, self.slug)


class InlineTask(TaskBase):
    kind: Literal[TaskKind.INLINE] = TaskKind.INLINE


class BasicTask(FileTaskBase):
    kind: Literal[TaskKind.BASIC] = TaskKind.BASIC


class ExtendedTask(FileTaskBase):
    kind: Literal[TaskKind.EXTENDED] = TaskKind.EXTENDED


AnyTask: TypeAlias = InlineTask | BasicTask | ExtendedTask


def build_task_ref(task_id: str, slug: str) -> str:
    return f"{task_id}-{slug}"


def is_root_task_id(task_id: str) -> bool:
    assert "-" not in task_id, "task id must be provided, not task ref"
    # HACK: tasks are in form s123t4567, root tasks are always s123 without `t` suffix
    return "t" not in task_id
