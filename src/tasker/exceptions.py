class TaskerError(Exception):
    def __init__(self, message: str, *, task_ref: str | None = None) -> None:
        super().__init__(message)
        self.task_ref = task_ref


class TaskValidateError(TaskerError):
    pass


class TaskHasSubtasksError(TaskerError):
    def __init__(
        self, task_id: str, *, pending_subtasks: list[tuple[str, str]]
    ) -> None:
        super().__init__(
            f"Task {task_id!r} has subtasks — its status is managed automatically.",
            task_ref=task_id,
        )
        self.pending_subtasks: list[tuple[str, str]] = pending_subtasks
