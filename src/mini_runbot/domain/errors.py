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

