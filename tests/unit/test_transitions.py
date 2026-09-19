import pytest

from mini_runbot.domain.enums import BuildStatus
from mini_runbot.domain.errors import InvalidTransitionError
from mini_runbot.domain.transitions import validate_transition


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (BuildStatus.NEW, BuildStatus.CHECKING_OUT),
        (BuildStatus.CHECKING_OUT, BuildStatus.PREPARING),
        (BuildStatus.PREPARING, BuildStatus.INSTALLING),
        (BuildStatus.INSTALLING, BuildStatus.TESTING),
        (BuildStatus.TESTING, BuildStatus.STARTING),
        (BuildStatus.STARTING, BuildStatus.RUNNING),
        (BuildStatus.RUNNING, BuildStatus.EXPIRED),
        (BuildStatus.FAILED, BuildStatus.DESTROYING),
        (BuildStatus.DESTROYING, BuildStatus.DESTROYED),
        (BuildStatus.DESTROYED, BuildStatus.DESTROYED),
    ],
)
def test_allowed_transitions(current: BuildStatus, target: BuildStatus) -> None:
    validate_transition(current, target)


@pytest.mark.parametrize("current", [BuildStatus.NEW, BuildStatus.INSTALLING, BuildStatus.TESTING])
def test_active_build_can_fail(current: BuildStatus) -> None:
    validate_transition(current, BuildStatus.FAILED)


def test_cannot_skip_pipeline_stages() -> None:
    with pytest.raises(InvalidTransitionError):
        validate_transition(BuildStatus.NEW, BuildStatus.RUNNING)


def test_destroyed_build_cannot_restart() -> None:
    with pytest.raises(InvalidTransitionError):
        validate_transition(BuildStatus.DESTROYED, BuildStatus.NEW)

