from datetime import datetime

from pydantic import BaseModel, ConfigDict

from mini_runbot.domain.enums import BuildStatus, StageStatus
from mini_runbot.domain.models import Build


class RepositoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    requested_ref: str
    commit_sha: str | None
    checkout_path: str | None
    addons_priority: int


class StageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    status: StageStatus
    started_at: datetime | None
    finished_at: datetime | None
    duration_seconds: float | None
    exit_code: int | None
    log_path: str | None
    summary: str | None


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
    stages: list[StageResponse]
    version: int
    odoo_version: str | None = None
    odoo_image: str | None = None
    postgres_image: str | None = None

    @classmethod
    def from_domain(cls, build: Build) -> "BuildResponse":
        return cls.model_validate(build)


class BuildLogsResponse(BaseModel):
    build_id: str
    stage: str | None
    content: str
    truncated_to_bytes: int


class RepositoryOptionResponse(BaseModel):
    alias: str
    default_ref: str
    allow_request_ref: bool
    addons_priority: int


class OdooVersionOptionResponse(BaseModel):
    name: str
    odoo_image: str
    postgres_image: str


class PublicConfigResponse(BaseModel):
    repositories: list[RepositoryOptionResponse]
    odoo_versions: list[OdooVersionOptionResponse] = []
    default_odoo_image: str | None = None
    default_ttl_seconds: int = 14_400
    max_concurrent_builds: int
