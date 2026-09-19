from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from mini_runbot.domain.enums import BuildStatus, StageStatus
from mini_runbot.domain.transitions import validate_transition


@dataclass(frozen=True, slots=True)
class RepositoryRevision:
    name: str
    source: str
    requested_ref: str
    commit_sha: str | None = None
    checkout_path: str | None = None
    addons_priority: int = 0


@dataclass(frozen=True, slots=True)
class StageResult:
    name: str
    status: StageStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_seconds: float | None = None
    exit_code: int | None = None
    log_path: str | None = None
    summary: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Build:
    id: str
    status: BuildStatus
    requested_ref: str
    repositories: list[RepositoryRevision]
    modules: list[str]
    created_at: datetime
    expires_at: datetime
    workspace_path: Path
    compose_project_name: str
    database_name: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    host_port: int | None = None
    preview_url: str | None = None
    failure_stage: str | None = None
    failure_message: str | None = None
    stages: list[StageResult] = field(default_factory=list)
    version: int = 1

    def transition_to(self, target: BuildStatus) -> None:
        validate_transition(self.status, target)
        self.status = target

