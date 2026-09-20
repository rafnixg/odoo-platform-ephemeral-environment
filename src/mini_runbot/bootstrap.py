from mini_runbot.adapters.git.cli import GitCliService
from mini_runbot.adapters.persistence.sqlite import SqliteBuildRepository
from mini_runbot.adapters.runtime.compose import DockerComposeRuntimeService
from mini_runbot.adapters.runtime.local import LocalRuntimeService
from mini_runbot.adapters.runtime.ports import SocketPortAllocator
from mini_runbot.application.build_manager import BuildManager
from mini_runbot.config import Settings


def create_manager(settings: Settings | None = None, *, docker: bool = False) -> BuildManager:
    settings = settings or Settings.from_environment()
    repository = SqliteBuildRepository(settings.database_url)
    repository.create_schema()
    runtime = (
        DockerComposeRuntimeService(settings)
        if docker and settings.repositories
        else LocalRuntimeService(settings.builds_root)
    )
    return BuildManager(
        repository,
        runtime,
        settings.builds_root,
        git=GitCliService(settings) if settings.repositories else None,
        port_allocator=SocketPortAllocator(
            settings.port_start, settings.port_end, lease_store=repository
        ),
        settings=settings,
    )
