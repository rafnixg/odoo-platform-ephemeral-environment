from typing import Protocol

from mini_runbot.domain.models import Build


class BuildRepository(Protocol):
    def add(self, build: Build) -> None: ...

    def get(self, build_id: str) -> Build | None: ...

    def list(self) -> list[Build]: ...

    def update(self, build: Build) -> None: ...

