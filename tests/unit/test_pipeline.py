from dataclasses import replace
from pathlib import Path

import pytest

from mini_runbot.application.build_manager import BuildManager
from mini_runbot.domain.enums import BuildStatus, StageStatus
from mini_runbot.domain.errors import RuntimeOperationError
from mini_runbot.domain.models import Build, RepositoryRevision
from mini_runbot.domain.validation import CreateBuildRequest
from mini_runbot.ports.services import CommandResult


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


class FakeGit:
    def checkout(
        self, revision: RepositoryRevision, workspace_path: Path, log_path: Path
    ) -> RepositoryRevision:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("checkout", encoding="utf-8")
        target = workspace_path / "sources" / revision.name
        return replace(revision, commit_sha="a" * 40, checkout_path=str(target))


class FakeRuntime:
    def __init__(self, fail_at: str | None = None) -> None:
        self.fail_at = fail_at
        self.calls: list[str] = []

    def prepare(self, build_id: str, workspace_path: Path) -> None:
        (workspace_path / "logs").mkdir(parents=True)

    def destroy(self, build_id: str, workspace_path: Path) -> None:
        self.calls.append("destroy")

    def _call(self, name: str, build: Build) -> CommandResult:
        self.calls.append(name)
        log = build.workspace_path / "logs" / f"{name}.log"
        log.write_text(name, encoding="utf-8")
        if self.fail_at == name:
            raise RuntimeOperationError(
                f"controlled {name} failure",
                exit_code=7,
                log_path=str(log),
            )
        return CommandResult(0, 0.01, str(log), f"{name} passed")

    def render(self, build: Build) -> CommandResult:
        return self._call("render", build)

    def validate(self, build: Build) -> CommandResult:
        return self._call("compose_validate", build)

    def start_database(self, build: Build) -> CommandResult:
        return self._call("database", build)

    def install_modules(self, build: Build) -> CommandResult:
        return self._call("install", build)

    def test_modules(self, build: Build) -> CommandResult:
        return self._call("test", build)

    def start_server(self, build: Build) -> CommandResult:
        return self._call("start", build)

    def wait_healthy(self, build: Build) -> CommandResult:
        return self._call("healthcheck", build)


class FixedPort:
    def __init__(self) -> None:
        self.released: list[int] = []

    def allocate(self, build_id: str, excluded: set[int] | None = None) -> int:
        return 18123

    def release(self, build_id: str, port: int) -> None:
        self.released.append(port)


def _manager(tmp_path: Path, runtime: FakeRuntime) -> BuildManager:
    return BuildManager(
        MemoryRepository(), runtime, tmp_path, git=FakeGit(), port_allocator=FixedPort()
    )


def test_successful_pipeline_reaches_running_with_separate_stages(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    manager = _manager(tmp_path, runtime)
    build = manager.create(
        CreateBuildRequest(repository="custom", ref="feature/x", modules=["module_a"])
    )

    result = manager.execute(build.id)

    assert result.status == BuildStatus.RUNNING
    assert result.repositories[0].commit_sha == "a" * 40
    assert result.preview_url == "http://127.0.0.1:18123"
    assert [item.name for item in result.stages] == [
        "checkout",
        "render",
        "compose_validate",
        "database",
        "install",
        "test",
        "start",
        "healthcheck",
    ]
    assert all(item.status == StageStatus.SUCCESS for item in result.stages)


@pytest.mark.parametrize("failure", ["install", "test", "healthcheck"])
def test_failure_prevents_publication_and_records_stage(tmp_path: Path, failure: str) -> None:
    runtime = FakeRuntime(fail_at=failure)
    manager = _manager(tmp_path, runtime)
    build = manager.create(
        CreateBuildRequest(repository="custom", ref="feature/x", modules=["module_a"])
    )

    with pytest.raises(RuntimeOperationError):
        manager.execute(build.id)

    failed = manager.get(build.id)
    assert failed.status == BuildStatus.FAILED
    assert failed.failure_stage == failure
    assert failed.stages[-1].status == StageStatus.FAILED
    assert failed.stages[-1].exit_code == 7
    assert failed.stages[-1].log_path
    assert runtime.calls[-1] == "destroy"
