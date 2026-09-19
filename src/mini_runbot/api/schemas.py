from datetime import datetime

from pydantic import BaseModel, ConfigDict

from mini_runbot.domain.enums import BuildStatus
from mini_runbot.domain.models import Build


class RepositoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    requested_ref: str
    commit_sha: str | None


class BuildResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: BuildStatus
    requested_ref: str
    repositories: list[RepositoryResponse]
    modules: list[str]
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    expires_at: datetime
    host_port: int | None
    preview_url: str | None
    failure_stage: str | None
    failure_message: str | None
    version: int

    @classmethod
    def from_domain(cls, build: Build) -> "BuildResponse":
        return cls.model_validate(build)
