from __future__ import annotations

import shutil
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from mini_runbot.config import Settings
from mini_runbot.domain.enums import BuildStatus, StageStatus
from mini_runbot.domain.errors import BuildNotFoundError, ConfigurationError, UnsafePathError
from mini_runbot.domain.models import (
    Build,
    CleanupResult,
    PurgeResult,
    RepositoryRevision,
    StageResult,
)
from mini_runbot.domain.validation import CreateBuildRequest
from mini_runbot.ports.repositories import BuildRepository
from mini_runbot.ports.services import (
    CommandResult,
    GitService,
    PortAllocator,
    RuntimeInspection,
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
                    exit_code=getattr(exc, "exit_code", None),
                    log_path=getattr(exc, "log_path", None),
                    summary=str(exc)[:1000],
                )
            )
            build.failure_stage = current_stage
            build.failure_message = str(exc)[:1000]
            build.finished_at = now
            if build.status not in {BuildStatus.DESTROYING, BuildStatus.DESTROYED}:
                build.transition_to(BuildStatus.FAILED)
            self.repository.update(build)
            self._cleanup_failed_execution(build)
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

    def _cleanup_failed_execution(self, build: Build) -> None:
        if self.settings and self.settings.retain_failed_runtime:
            return
        try:
            self.runtime.destroy(build.id, build.workspace_path)
        except Exception as cleanup_error:
            build.failure_message = (
                f"{build.failure_message}; runtime cleanup failed: {cleanup_error}"
            )[:1000]
            self.repository.update(build)
            return
        if self.port_allocator and build.host_port:
            self.port_allocator.release(build.id, build.host_port)

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

    def purge_destroyed(self, now: datetime | None = None) -> PurgeResult:
        retention = self.settings.destroyed_retention_seconds if self.settings else 0
        builds = self.list()
        if retention <= 0:
            return PurgeResult(len(builds), [], [])
        cutoff = (now or datetime.now(UTC)) - timedelta(seconds=retention)
        purged: list[str] = []
        failed: list[str] = []
        for build in builds:
            finished_at = build.finished_at
            if build.status != BuildStatus.DESTROYED or finished_at is None:
                continue
            if finished_at.tzinfo is None:
                finished_at = finished_at.replace(tzinfo=UTC)
            if finished_at > cutoff:
                continue
            try:
                workspace = build.workspace_path.resolve()
                expected = (self.builds_root / build.id).resolve()
                if workspace != expected or workspace.parent != self.builds_root:
                    raise UnsafePathError(
                        f"Workspace is outside configured root: {workspace}"
                    )
                if workspace.exists():
                    shutil.rmtree(workspace)
                self.repository.delete(build.id)
                purged.append(build.id)
            except Exception:
                failed.append(build.id)
        return PurgeResult(len(builds), purged, failed)

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
                    self._cleanup_recovered_runtime(build)
                    recovered.append(build.id)
                elif build.status == BuildStatus.RUNNING:
                    inspection = self._inspect_runtime(build)
                    if inspection is not None and not inspection.running:
                        build.failure_stage = "recovery"
                        build.failure_message = inspection.summary
                        build.finished_at = datetime.now(UTC)
                        build.transition_to(BuildStatus.FAILED)
                        self.repository.update(build)
                        self._cleanup_recovered_runtime(build, inspection)
                        recovered.append(build.id)
            except Exception:
                failed.append(build.id)
        reconcile = getattr(self.port_allocator, "reconcile", None)
        if callable(reconcile):
            reconcile()
        return CleanupResult(len(builds), recovered, failed)

    def _inspect_runtime(self, build: Build) -> RuntimeInspection | None:
        inspect_runtime = getattr(self.runtime, "inspect", None)
        if not callable(inspect_runtime):
            return None
        return inspect_runtime(build)

    def _cleanup_recovered_runtime(
        self, build: Build, inspection: RuntimeInspection | None = None
    ) -> None:
        if self.settings and self.settings.retain_failed_runtime:
            return
        inspection = inspection or self._inspect_runtime(build)
        if inspection is None:
            return
        if inspection.exists:
            self.runtime.destroy(build.id, build.workspace_path)
        if self.port_allocator and build.host_port:
            self.port_allocator.release(build.id, build.host_port)
