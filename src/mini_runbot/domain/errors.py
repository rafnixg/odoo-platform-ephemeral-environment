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
    pass


class BuildExecutionError(MiniRunbotError):
    def __init__(self, stage: str, message: str) -> None:
        super().__init__(message)
        self.stage = stage
