from datetime import UTC, datetime, timedelta
from pathlib import Path

from mini_runbot.application.build_manager import BuildManager
from mini_runbot.config import RepositoryConfig, Settings
from mini_runbot.domain.enums import BuildStatus
from mini_runbot.domain.models import Build
from mini_runbot.domain.validation import CreateBuildRequest
from mini_runbot.ports.services import RuntimeInspection


class MemoryRepository:
    def __init__(self) -> None:
        self.items: dict[str, Build] = {}

    def add(self, build: Build) -> None:
        self.items[build.id] = build

    def get(self, build_id: str) -> Build | None:
        return self.items.get(build_id)

    def list(self) -> list[Build]:
        return list(self.items.values())

    def update(self, build: Build) -> None:
        build.version += 1

    def delete(self, build_id: str) -> None:
        self.items.pop(build_id, None)


class Runtime:
    def __init__(self) -> None:
        self.destroyed: list[str] = []

    def prepare(self, build_id: str, workspace_path: Path) -> None:
        workspace_path.mkdir(parents=True)

    def destroy(self, build_id: str, workspace_path: Path) -> None:
        self.destroyed.append(build_id)


class InspectableRuntime(Runtime):
    def __init__(self, inspection: RuntimeInspection) -> None:
        super().__init__()
        self.inspection = inspection

    def inspect(self, build: Build) -> RuntimeInspection:
        return self.inspection


class Ports:
    def __init__(self) -> None:
        self.released: list[int] = []

    def allocate(self, build_id: str, excluded: set[int] | None = None) -> int:
        return 18123

    def release(self, build_id: str, port: int) -> None:
        self.released.append(port)

    def reconcile(self) -> list[int]:
        return []


def test_cleanup_destroys_expired_build_and_releases_port(tmp_path: Path) -> None:
    repository = MemoryRepository()
    runtime = Runtime()
    ports = Ports()
    manager = BuildManager(repository, runtime, tmp_path, port_allocator=ports)
    build = manager.create(
        CreateBuildRequest(
            repository="custom", ref="HEAD", modules=["demo"], ttl_seconds=300
        )
    )

    result = manager.cleanup_expired(build.expires_at + timedelta(seconds=1))

    assert result.destroyed_ids == [build.id]
    assert manager.get(build.id).status == BuildStatus.DESTROYED
    assert runtime.destroyed == [build.id]
    assert ports.released == [18123]


def test_recovery_marks_interrupted_build_failed(tmp_path: Path) -> None:
    repository = MemoryRepository()
    manager = BuildManager(repository, Runtime(), tmp_path)
    build = manager.create(
        CreateBuildRequest(repository="custom", ref="HEAD", modules=["demo"])
    )
    build.transition_to(BuildStatus.CHECKING_OUT)
    repository.update(build)

    result = manager.recover_interrupted()

    assert result.destroyed_ids == [build.id]
    assert build.status == BuildStatus.FAILED
    assert build.failure_stage == "recovery"


def test_recovery_marks_running_build_failed_when_runtime_is_missing(
    tmp_path: Path,
) -> None:
    repository = MemoryRepository()
    runtime = InspectableRuntime(
        RuntimeInspection(False, False, (), "Compose configuration is absent")
    )
    ports = Ports()
    manager = BuildManager(
        repository, runtime, tmp_path, port_allocator=ports
    )
    build = manager.create(
        CreateBuildRequest(repository="custom", ref="HEAD", modules=["demo"])
    )
    build.status = BuildStatus.RUNNING
    repository.update(build)

    result = manager.recover_interrupted()

    assert result.destroyed_ids == [build.id]
    assert build.status == BuildStatus.FAILED
    assert build.failure_message == "Compose configuration is absent"
    assert runtime.destroyed == []
    assert ports.released == [18123]


def test_recovery_keeps_healthy_running_build(tmp_path: Path) -> None:
    repository = MemoryRepository()
    runtime = InspectableRuntime(
        RuntimeInspection(True, True, ("db", "odoo"), "Docker runtime is running")
    )
    ports = Ports()
    manager = BuildManager(
        repository, runtime, tmp_path, port_allocator=ports
    )
    build = manager.create(
        CreateBuildRequest(repository="custom", ref="HEAD", modules=["demo"])
    )
    build.status = BuildStatus.RUNNING
    repository.update(build)

    result = manager.recover_interrupted()

    assert result.destroyed_ids == []
    assert build.status == BuildStatus.RUNNING
    assert runtime.destroyed == []
    assert ports.released == []


def test_retention_purges_old_destroyed_build_and_workspace(tmp_path: Path) -> None:
    repository = MemoryRepository()
    runtime = Runtime()
    settings = Settings(
        builds_root=tmp_path,
        destroyed_retention_seconds=60,
        repositories={
            "custom": RepositoryConfig(url=str(tmp_path), target="custom")
        },
    )
    manager = BuildManager(
        repository, runtime, tmp_path, settings=settings
    )
    build = manager.create(
        CreateBuildRequest(repository="custom", ref="HEAD", modules=["demo"])
    )
    evidence = build.workspace_path / "logs" / "evidence.log"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text("audit", encoding="utf-8")
    manager.destroy(build.id)
    build.finished_at = datetime.now(UTC) - timedelta(minutes=2)
    repository.update(build)

    result = manager.purge_destroyed()

    assert result.purged_ids == [build.id]
    assert repository.get(build.id) is None
    assert not build.workspace_path.exists()


def test_retention_refuses_workspace_outside_build_root(tmp_path: Path) -> None:
    repository = MemoryRepository()
    settings = Settings(
        builds_root=tmp_path / "builds",
        destroyed_retention_seconds=1,
        repositories={
            "custom": RepositoryConfig(url=str(tmp_path), target="custom")
        },
    )
    manager = BuildManager(
        repository, Runtime(), settings.builds_root, settings=settings
    )
    build = manager.create(
        CreateBuildRequest(repository="custom", ref="HEAD", modules=["demo"])
    )
    manager.destroy(build.id)
    outside = tmp_path / "outside"
    outside.mkdir()
    build.workspace_path = outside
    build.finished_at = datetime.now(UTC) - timedelta(minutes=1)
    repository.update(build)

    result = manager.purge_destroyed()

    assert result.failed_ids == [build.id]
    assert outside.exists()
    assert repository.get(build.id) is not None
