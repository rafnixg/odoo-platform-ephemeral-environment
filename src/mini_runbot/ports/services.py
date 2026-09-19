from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from mini_runbot.domain.models import Build, RepositoryRevision


@dataclass(frozen=True, slots=True)
class CommandResult:
    exit_code: int
    duration_seconds: float
    log_path: str
    summary: str


class GitService(Protocol):
    def checkout(
        self,
        revision: RepositoryRevision,
        workspace_path: Path,
        log_path: Path,
    ) -> RepositoryRevision: ...


class PortAllocator(Protocol):
    def allocate(self) -> int: ...

    def release(self, port: int) -> None: ...


class RuntimeService(Protocol):
    def prepare(self, build_id: str, workspace_path: Path) -> None: ...

    def destroy(self, build_id: str, workspace_path: Path) -> None: ...


class BuildRuntimeService(RuntimeService, Protocol):
    def render(self, build: Build) -> CommandResult: ...

    def validate(self, build: Build) -> CommandResult: ...

    def start_database(self, build: Build) -> CommandResult: ...

    def install_modules(self, build: Build) -> CommandResult: ...

    def test_modules(self, build: Build) -> CommandResult: ...

    def start_server(self, build: Build) -> CommandResult: ...

    def wait_healthy(self, build: Build) -> CommandResult: ...
