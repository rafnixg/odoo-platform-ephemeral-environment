from datetime import timedelta
from pathlib import Path

from mini_runbot.application.build_manager import BuildManager
from mini_runbot.domain.enums import BuildStatus
from mini_runbot.domain.models import Build
from mini_runbot.domain.validation import CreateBuildRequest


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


class Runtime:
    def __init__(self) -> None:
        self.destroyed: list[str] = []

    def prepare(self, build_id: str, workspace_path: Path) -> None:
        workspace_path.mkdir(parents=True)

    def destroy(self, build_id: str, workspace_path: Path) -> None:
        self.destroyed.append(build_id)


class Ports:
    def __init__(self) -> None:
        self.released: list[int] = []

    def allocate(self, build_id: str, excluded: set[int] | None = None) -> int:
        return 18123

    def release(self, build_id: str, port: int) -> None:
        self.released.append(port)


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
