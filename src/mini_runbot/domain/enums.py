from enum import StrEnum


class BuildStatus(StrEnum):
    NEW = "new"
    CHECKING_OUT = "checking_out"
    PREPARING = "preparing"
    INSTALLING = "installing"
    TESTING = "testing"
    STARTING = "starting"
    RUNNING = "running"
    FAILED = "failed"
    EXPIRED = "expired"
    DESTROYING = "destroying"
    DESTROYED = "destroyed"


class StageStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"

