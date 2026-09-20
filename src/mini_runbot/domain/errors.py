class MiniRunbotError(Exception):
    """Base error for safe application-level handling."""


class BuildNotFoundError(MiniRunbotError):
    pass


class InvalidTransitionError(MiniRunbotError):
    pass


class ConcurrentUpdateError(MiniRunbotError):
    pass


class UnsafePathError(MiniRunbotError):
    pass


class ConfigurationError(MiniRunbotError):
    pass


class GitOperationError(MiniRunbotError):
    pass


class RuntimeOperationError(MiniRunbotError):
    def __init__(
        self,
        message: str,
        *,
        exit_code: int | None = None,
        log_path: str | None = None,
    ) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.log_path = log_path


class BuildExecutionError(MiniRunbotError):
    def __init__(self, stage: str, message: str) -> None:
        super().__init__(message)
        self.stage = stage
