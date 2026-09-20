from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from mini_runbot.adapters.persistence.sqlite import SqliteBuildRepository
from mini_runbot.adapters.runtime.local import LocalRuntimeService
from mini_runbot.adapters.runtime.ports import SocketPortAllocator
from mini_runbot.application.build_manager import BuildManager
from mini_runbot.domain.validation import CreateBuildRequest


def test_separate_managers_exclude_ports_persisted_by_other_processes(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'ports.db'}"
    builds_root = tmp_path / "builds"
    first_repository = SqliteBuildRepository(database_url)
    first_repository.create_schema()
    second_repository = SqliteBuildRepository(database_url)
    second_repository.create_schema()
    first = BuildManager(
        first_repository,
        LocalRuntimeService(builds_root),
        builds_root,
        port_allocator=SocketPortAllocator(32301, 32302, first_repository),
    )
    second = BuildManager(
        second_repository,
        LocalRuntimeService(builds_root),
        builds_root,
        port_allocator=SocketPortAllocator(32301, 32302, second_repository),
    )
    request = CreateBuildRequest(repository="custom", ref="HEAD", modules=["demo"])

    first_build = first.create(request)
    second_build = second.create(request)

    assert first_build.host_port != second_build.host_port


def test_concurrent_managers_acquire_distinct_persistent_leases(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'concurrent-ports.db'}"
    builds_root = tmp_path / "builds"
    repositories = [SqliteBuildRepository(database_url) for _ in range(2)]
    for repository in repositories:
        repository.create_schema()
    managers = [
        BuildManager(
            repository,
            LocalRuntimeService(builds_root),
            builds_root,
            port_allocator=SocketPortAllocator(32311, 32312, repository),
        )
        for repository in repositories
    ]
    barrier = Barrier(2)

    def create(manager: BuildManager) -> int | None:
        barrier.wait()
        return manager.create(
            CreateBuildRequest(repository="custom", ref="HEAD", modules=["demo"])
        ).host_port

    with ThreadPoolExecutor(max_workers=2) as pool:
        ports = list(pool.map(create, managers))

    assert len(set(ports)) == 2


def test_destroy_releases_persistent_lease_for_reuse(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'release-port.db'}"
    builds_root = tmp_path / "builds"
    repository = SqliteBuildRepository(database_url)
    repository.create_schema()
    manager = BuildManager(
        repository,
        LocalRuntimeService(builds_root),
        builds_root,
        port_allocator=SocketPortAllocator(32321, 32321, repository),
    )
    request = CreateBuildRequest(repository="custom", ref="HEAD", modules=["demo"])

    first = manager.create(request)
    manager.destroy(first.id)
    second = manager.create(request)

    assert first.host_port == second.host_port == 32321


def test_recovery_releases_orphaned_lease(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'orphan-port.db'}"
    builds_root = tmp_path / "builds"
    repository = SqliteBuildRepository(database_url)
    repository.create_schema()
    assert repository.try_acquire_port("missing-build", 32331)
    allocator = SocketPortAllocator(32331, 32331, repository)
    manager = BuildManager(
        repository,
        LocalRuntimeService(builds_root),
        builds_root,
        port_allocator=allocator,
    )

    result = manager.recover_interrupted()
    build = manager.create(
        CreateBuildRequest(repository="custom", ref="HEAD", modules=["demo"])
    )

    assert result.examined == 0
    assert build.host_port == 32331
