from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from mini_runbot.domain.enums import BuildStatus
from mini_runbot.domain.errors import BuildNotFoundError
from mini_runbot.domain.models import Build, RepositoryRevision
from mini_runbot.domain.validation import CreateBuildRequest
from mini_runbot.ports.repositories import BuildRepository
from mini_runbot.ports.services import RuntimeService


class BuildManager:
    def __init__(
        self,
        repository: BuildRepository,
        runtime: RuntimeService,
        builds_root: Path,
    ) -> None:
        self.repository = repository
        self.runtime = runtime
        self.builds_root = builds_root.resolve()

    def create(self, request: CreateBuildRequest) -> Build:
        now = datetime.now(UTC)
        build_id = f"build-{now:%Y%m%d}-{uuid4().hex[:12]}"
        workspace = self.builds_root / build_id
        build = Build(
            id=build_id,
            status=BuildStatus.NEW,
            requested_ref=request.ref,
            repositories=[
                RepositoryRevision(
                    name=request.repository,
                    source=request.repository,
                    requested_ref=request.ref,
                )
            ],
            modules=list(request.modules),
            created_at=now,
            expires_at=now + timedelta(seconds=request.ttl_seconds),
            workspace_path=workspace,
            compose_project_name=build_id.replace("-", "_"),
            database_name=build_id.replace("-", "_"),
        )
        self.repository.add(build)
        try:
            self.runtime.prepare(build.id, build.workspace_path)
        except Exception as exc:
            build.failure_stage = "prepare_workspace"
            build.failure_message = str(exc)[:1000]
            build.transition_to(BuildStatus.FAILED)
            build.finished_at = datetime.now(UTC)
            self.repository.update(build)
            raise
        return build

    def get(self, build_id: str) -> Build:
        build = self.repository.get(build_id)
        if build is None:
            raise BuildNotFoundError(f"Build {build_id} was not found")
        return build

    def list(self) -> list[Build]:
        return self.repository.list()

    def destroy(self, build_id: str) -> Build:
        build = self.get(build_id)
        if build.status == BuildStatus.DESTROYED:
            return build
        if build.status != BuildStatus.DESTROYING:
            build.transition_to(BuildStatus.DESTROYING)
            self.repository.update(build)
        self.runtime.destroy(build.id, build.workspace_path)
        build.transition_to(BuildStatus.DESTROYED)
        build.finished_at = datetime.now(UTC)
        self.repository.update(build)
        return build

