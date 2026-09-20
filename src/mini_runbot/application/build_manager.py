from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from mini_runbot.config import Settings
from mini_runbot.domain.enums import BuildStatus, StageStatus
from mini_runbot.domain.errors import BuildNotFoundError, ConfigurationError, UnsafePathError
from mini_runbot.domain.models import Build, CleanupResult, RepositoryRevision, StageResult
from mini_runbot.domain.validation import CreateBuildRequest
from mini_runbot.ports.repositories import BuildRepository
from mini_runbot.ports.services import (
    CommandResult,
    GitService,
    PortAllocator,
    RuntimeService,
)


class BuildManager:
    def __init__(
        self,
        repository: BuildRepository,
        runtime: RuntimeService,
        builds_root: Path,
        git: GitService | None = None,
        port_allocator: PortAllocator | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.repository = repository
        self.runtime = runtime
        self.builds_root = builds_root.resolve()
        self.git = git
        self.port_allocator = port_allocator
        self.settings = settings

    def create(self, request: CreateBuildRequest) -> Build:
        now = datetime.now(UTC)
        build_id = f"build-{now:%Y%m%d}-{uuid4().hex[:12]}"
        workspace = self.builds_root / build_id
        selected_repositories = request.selected_repositories
        revisions: list[RepositoryRevision] = []
        for selected in selected_repositories:
            source = selected.repository
            priority = 0
            if self.settings is not None:
                configured = self.settings.repository(selected.repository, selected.ref)
                source = configured.url
                priority = configured.addons_priority
            revisions.append(
                RepositoryRevision(
                    name=selected.repository,
                    source=source,
                    requested_ref=selected.ref,
                    addons_priority=priority,
                )
            )
        terminal = {BuildStatus.DESTROYED}
        used_ports = {
            item.host_port
            for item in self.repository.list()
            if item.host_port is not None and item.status not in terminal
        }
        host_port = (
            self.port_allocator.allocate(build_id, used_ports) if self.port_allocator else None
        )
        build = Build(
            id=build_id,
            status=BuildStatus.NEW,
            requested_ref=selected_repositories[0].ref,
            repositories=revisions,
            modules=list(request.modules),
            created_at=now,
            expires_at=now + timedelta(seconds=request.ttl_seconds),
            workspace_path=workspace,
            compose_project_name=build_id.replace("-", "_"),
            database_name=build_id.replace("-", "_"),
            host_port=host_port,
            preview_url=f"http://127.0.0.1:{host_port}" if host_port else None,
        )
        try:
            self.repository.add(build)
        except Exception:
            if self.port_allocator and build.host_port:
                self.port_allocator.release(build.id, build.host_port)
            raise
        try:
            self.runtime.prepare(build.id, build.workspace_path)
        except Exception as exc:
            if self.port_allocator and build.host_port:
                self.port_allocator.release(build.id, build.host_port)
            build.failure_stage = "prepare_workspace"
            build.failure_message = str(exc)[:1000]
            build.transition_to(BuildStatus.FAILED)
            build.finished_at = datetime.now(UTC)
            self.repository.update(build)
            raise
        return build

    def execute(self, build_id: str) -> Build:
        build = self.get(build_id)
        if build.status != BuildStatus.NEW:
            raise ConfigurationError(f"Only new builds can execute; {build.id} is {build.status}")
        if self.git is None or not self._is_build_runtime(self.runtime):
            raise ConfigurationError("Git and Docker Compose adapters are not configured")

        build.started_at = datetime.now(UTC)
        current_stage = "checkout"
        try:
            build.transition_to(BuildStatus.CHECKING_OUT)
            self.repository.update(build)
            checkout_started = time.monotonic()
            resolved = []
            checkout_log = build.workspace_path / "logs" / "checkout.log"
            for revision in build.repositories:
                resolved.append(self.git.checkout(revision, build.workspace_path, checkout_log))
            build.repositories = resolved
            self._success_stage(
                build,
                current_stage,
                CommandResult(
                    exit_code=0,
                    duration_seconds=time.monotonic() - checkout_started,
                    log_path=str(checkout_log),
                    summary="Git references resolved and checked out",
                ),
            )

            build.transition_to(BuildStatus.PREPARING)
            self.repository.update(build)
            current_stage = "render"
            self._success_stage(build, current_stage, self.runtime.render(build))
            current_stage = "compose_validate"
            self._success_stage(build, current_stage, self.runtime.validate(build))
            current_stage = "database"
            self._success_stage(build, current_stage, self.runtime.start_database(build))

            build.transition_to(BuildStatus.INSTALLING)
            self.repository.update(build)
            current_stage = "install"
            self._success_stage(build, current_stage, self.runtime.install_modules(build))

            build.transition_to(BuildStatus.TESTING)
            self.repository.update(build)
            current_stage = "test"
            self._success_stage(build, current_stage, self.runtime.test_modules(build))

            build.transition_to(BuildStatus.STARTING)
            self.repository.update(build)
            current_stage = "start"
            self._success_stage(build, current_stage, self.runtime.start_server(build))
            current_stage = "healthcheck"
            self._success_stage(build, current_stage, self.runtime.wait_healthy(build))

            build.transition_to(BuildStatus.RUNNING)
            self.repository.update(build)
            return build
        except Exception as exc:
            now = datetime.now(UTC)
            build.stages.append(
                StageResult(
                    name=current_stage,
                    status=StageStatus.FAILED,
                    started_at=now,
                    finished_at=now,
                    duration_seconds=0,
                    summary=str(exc)[:1000],
                )
            )
            build.failure_stage = current_stage
            build.failure_message = str(exc)[:1000]
            build.finished_at = now
            if build.status not in {BuildStatus.DESTROYING, BuildStatus.DESTROYED}:
                build.transition_to(BuildStatus.FAILED)
            self.repository.update(build)
            raise

    def get(self, build_id: str) -> Build:
        build = self.repository.get(build_id)
        if build is None:
            raise BuildNotFoundError(f"Build {build_id} was not found")
        return build

    def _success_stage(self, build: Build, name: str, result: CommandResult) -> None:
        finished = datetime.now(UTC)
        build.stages.append(
            StageResult(
                name=name,
                status=StageStatus.SUCCESS,
                started_at=finished - timedelta(seconds=result.duration_seconds),
                finished_at=finished,
                duration_seconds=result.duration_seconds,
                exit_code=result.exit_code,
                log_path=result.log_path,
                summary=result.summary,
            )
        )
        self.repository.update(build)

    @staticmethod
    def _is_build_runtime(runtime: RuntimeService) -> bool:
        methods = (
            "render",
            "validate",
            "start_database",
            "install_modules",
            "test_modules",
            "start_server",
            "wait_healthy",
        )
        return all(callable(getattr(runtime, method, None)) for method in methods)

    def list(self) -> list[Build]:
        return self.repository.list()

    @property
    def execution_ready(self) -> bool:
        return self.git is not None and self._is_build_runtime(self.runtime)

    def read_logs(self, build_id: str, stage: str | None = None, max_bytes: int = 100_000) -> str:
        build = self.get(build_id)
        logs_root = (build.workspace_path / "logs").resolve()
        selected = [item for item in build.stages if stage is None or item.name == stage]
        chunks: list[str] = []
        for item in selected:
            if not item.log_path:
                continue
            path = Path(item.log_path).resolve()
            if path.parent != logs_root:
                raise UnsafePathError(
                    f"Recorded log path is outside the build log directory: {path}"
                )
            if path.is_file():
                content = path.read_bytes()[-max_bytes:].decode("utf-8", errors="replace")
                chunks.append(f"== {item.name} ==\n{content}")
        return "\n".join(chunks)[-max_bytes:]

    def destroy(self, build_id: str) -> Build:
        build = self.get(build_id)
        if build.status == BuildStatus.DESTROYED:
            return build
        if build.status != BuildStatus.DESTROYING:
            build.transition_to(BuildStatus.DESTROYING)
            self.repository.update(build)
        self.runtime.destroy(build.id, build.workspace_path)
        if self.port_allocator and build.host_port:
            self.port_allocator.release(build.id, build.host_port)
        build.transition_to(BuildStatus.DESTROYED)
        build.finished_at = datetime.now(UTC)
        self.repository.update(build)
        return build

    def cleanup_expired(self, now: datetime | None = None) -> CleanupResult:
        cutoff = now or datetime.now(UTC)
        destroyed: list[str] = []
        failed: list[str] = []
        builds = self.list()
        for build in builds:
            expires_at = build.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if expires_at > cutoff or build.status == BuildStatus.DESTROYED:
                continue
            try:
                if build.status == BuildStatus.RUNNING:
                    build.transition_to(BuildStatus.EXPIRED)
                    self.repository.update(build)
                self.destroy(build.id)
                destroyed.append(build.id)
            except Exception:
                failed.append(build.id)
        return CleanupResult(len(builds), destroyed, failed)

    def recover_interrupted(self) -> CleanupResult:
        active = {
            BuildStatus.CHECKING_OUT,
            BuildStatus.PREPARING,
            BuildStatus.INSTALLING,
            BuildStatus.TESTING,
            BuildStatus.STARTING,
        }
        recovered: list[str] = []
        failed: list[str] = []
        builds = self.list()
        for build in builds:
            try:
                if build.status == BuildStatus.DESTROYING:
                    self.destroy(build.id)
                    recovered.append(build.id)
                elif build.status in active:
                    build.failure_stage = "recovery"
                    build.failure_message = "Build was interrupted by an orchestrator restart"
                    build.finished_at = datetime.now(UTC)
                    build.transition_to(BuildStatus.FAILED)
                    self.repository.update(build)
                    recovered.append(build.id)
            except Exception:
                failed.append(build.id)
        if self.port_allocator:
            self.port_allocator.reconcile()
        return CleanupResult(len(builds), recovered, failed)
