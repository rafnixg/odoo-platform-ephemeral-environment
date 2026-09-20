from pathlib import Path

import pytest

from mini_runbot.application.build_manager import BuildManager
from mini_runbot.config import RepositoryConfig, Settings
from mini_runbot.domain.enums import BuildStatus
from mini_runbot.domain.errors import ConfigurationError
from mini_runbot.domain.models import Build
from mini_runbot.domain.validation import CreateBuildRequest, RequestedRepository


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
        self.items[build.id] = build


class SpyRuntime:
    def __init__(self) -> None:
        self.prepare_calls = 0
        self.destroy_calls = 0

    def prepare(self, build_id: str, workspace_path: Path) -> None:
        self.prepare_calls += 1

    def destroy(self, build_id: str, workspace_path: Path) -> None:
        self.destroy_calls += 1


def test_create_and_destroy_are_persisted_and_destroy_is_idempotent(tmp_path: Path) -> None:
    repository = MemoryRepository()
    runtime = SpyRuntime()
    manager = BuildManager(repository, runtime, tmp_path)
    request = CreateBuildRequest(repository="custom", ref="feature/x", modules=["module_a"])

    build = manager.create(request)
    first_result = manager.destroy(build.id)
    second_result = manager.destroy(build.id)

    assert build.status == BuildStatus.DESTROYED
    assert first_result.id == second_result.id
    assert runtime.prepare_calls == 1
    assert runtime.destroy_calls == 1
    assert manager.get(build.id).status == BuildStatus.DESTROYED


def test_ids_and_resource_names_are_unique_and_safe(tmp_path: Path) -> None:
    manager = BuildManager(MemoryRepository(), SpyRuntime(), tmp_path)
    request = CreateBuildRequest(repository="custom", ref="16.0", modules=["base"])

    first = manager.create(request)
    second = manager.create(request)

    assert first.id != second.id
    assert first.id.startswith("build-")
    assert first.compose_project_name.replace("_", "").isalnum()
    assert first.workspace_path.parent == tmp_path.resolve()


def test_configured_manager_rejects_create_without_repository_alias(tmp_path: Path) -> None:
    manager = BuildManager(
        MemoryRepository(),
        SpyRuntime(),
        tmp_path,
        settings=Settings(builds_root=tmp_path),
    )
    request = CreateBuildRequest(repository="custom", ref="16.0", modules=["base"])

    with pytest.raises(ConfigurationError, match="Repository alias is not allowed"):
        manager.create(request)


def test_create_persists_multiple_configured_repositories(tmp_path: Path) -> None:
    settings = Settings(
        builds_root=tmp_path,
        repositories={
            "oca": RepositoryConfig(
                url="https://github.com/OCA/e-commerce.git",
                target="oca-ecommerce",
                addons_priority=200,
            ),
            "custom": RepositoryConfig(
                url="https://github.com/example/custom.git",
                target="custom-addons",
                addons_priority=100,
            ),
        },
    )
    manager = BuildManager(
        MemoryRepository(), SpyRuntime(), tmp_path, settings=settings
    )

    build = manager.create(
        CreateBuildRequest(
            repositories=[
                RequestedRepository(repository="oca", ref="16.0"),
                RequestedRepository(repository="custom", ref="feature/multi"),
            ],
            modules=["website_sale_hide_price"],
        )
    )

    actual = [
        (item.name, item.requested_ref, item.addons_priority)
        for item in build.repositories
    ]
    assert actual == [
        ("oca", "16.0", 200),
        ("custom", "feature/multi", 100),
    ]
