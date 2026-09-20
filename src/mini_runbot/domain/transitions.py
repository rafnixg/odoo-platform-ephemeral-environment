from mini_runbot.domain.enums import BuildStatus
from mini_runbot.domain.errors import InvalidTransitionError

_FORWARD: dict[BuildStatus, frozenset[BuildStatus]] = {
    BuildStatus.NEW: frozenset({BuildStatus.CHECKING_OUT}),
    BuildStatus.CHECKING_OUT: frozenset({BuildStatus.PREPARING}),
    BuildStatus.PREPARING: frozenset({BuildStatus.INSTALLING}),
    BuildStatus.INSTALLING: frozenset({BuildStatus.TESTING}),
    BuildStatus.TESTING: frozenset({BuildStatus.STARTING}),
    BuildStatus.STARTING: frozenset({BuildStatus.RUNNING}),
    BuildStatus.RUNNING: frozenset({BuildStatus.EXPIRED}),
    BuildStatus.FAILED: frozenset(),
    BuildStatus.EXPIRED: frozenset(),
    BuildStatus.DESTROYING: frozenset({BuildStatus.DESTROYED}),
    BuildStatus.DESTROYED: frozenset(),
}

_CAN_FAIL = {
    BuildStatus.NEW,
    BuildStatus.CHECKING_OUT,
    BuildStatus.PREPARING,
    BuildStatus.INSTALLING,
    BuildStatus.TESTING,
    BuildStatus.STARTING,
    BuildStatus.RUNNING,
}

_CAN_DESTROY = set(BuildStatus) - {BuildStatus.DESTROYING, BuildStatus.DESTROYED}


def can_transition(current: BuildStatus, target: BuildStatus) -> bool:
    if current == target:
        return current == BuildStatus.DESTROYED
    if target == BuildStatus.FAILED:
        return current in _CAN_FAIL
    if target == BuildStatus.DESTROYING:
        return current in _CAN_DESTROY
    return target in _FORWARD[current]


def validate_transition(current: BuildStatus, target: BuildStatus) -> None:
    if not can_transition(current, target):
        raise InvalidTransitionError(f"Cannot transition build from {current} to {target}")
