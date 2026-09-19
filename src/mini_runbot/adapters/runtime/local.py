import shutil
from pathlib import Path

from mini_runbot.domain.errors import UnsafePathError


class LocalRuntimeService:
    """Controlled Phase 0 runtime that owns only a per-build runtime directory."""

    def __init__(self, builds_root: Path) -> None:
        self.builds_root = builds_root.resolve()

    def _validate_workspace(self, build_id: str, workspace_path: Path) -> Path:
        expected = (self.builds_root / build_id).resolve()
        actual = workspace_path.resolve()
        if actual != expected or actual.parent != self.builds_root:
            raise UnsafePathError(f"Workspace is outside the configured build root: {actual}")
        return actual

    def prepare(self, build_id: str, workspace_path: Path) -> None:
        workspace = self._validate_workspace(build_id, workspace_path)
        (workspace / "logs").mkdir(parents=True, exist_ok=True)
        (workspace / "runtime").mkdir(parents=True, exist_ok=True)

    def destroy(self, build_id: str, workspace_path: Path) -> None:
        workspace = self._validate_workspace(build_id, workspace_path)
        runtime_path = workspace / "runtime"
        if runtime_path.exists():
            shutil.rmtree(runtime_path)

