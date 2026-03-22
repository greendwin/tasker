class TaskerError(Exception):
    def __init__(self, message: str, *, task_ref: str | None = None) -> None:
        super().__init__(message)
        self.task_ref = task_ref


class TaskValidateError(TaskerError):
    pass
