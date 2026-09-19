from mini_runbot.adapters.persistence.sqlite import SqliteBuildRepository
from mini_runbot.adapters.runtime.local import LocalRuntimeService
from mini_runbot.application.build_manager import BuildManager
from mini_runbot.config import Settings


def create_manager(settings: Settings | None = None) -> BuildManager:
    settings = settings or Settings.from_environment()
    repository = SqliteBuildRepository(settings.database_url)
    repository.create_schema()
    runtime = LocalRuntimeService(settings.builds_root)
    return BuildManager(repository, runtime, settings.builds_root)

