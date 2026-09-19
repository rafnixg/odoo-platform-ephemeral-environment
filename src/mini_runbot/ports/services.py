from pathlib import Path
from typing import Protocol


class RuntimeService(Protocol):
    def prepare(self, build_id: str, workspace_path: Path) -> None: ...

    def destroy(self, build_id: str, workspace_path: Path) -> None: ...

