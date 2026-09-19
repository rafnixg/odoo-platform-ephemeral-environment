from pathlib import Path

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
        port_allocator=SocketPortAllocator(32301, 32302),
    )
    second = BuildManager(
        second_repository,
        LocalRuntimeService(builds_root),
        builds_root,
        port_allocator=SocketPortAllocator(32301, 32302),
    )
    request = CreateBuildRequest(repository="custom", ref="HEAD", modules=["demo"])

    first_build = first.create(request)
    second_build = second.create(request)

    assert first_build.host_port != second_build.host_port
