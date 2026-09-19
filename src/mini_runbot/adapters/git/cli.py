from __future__ import annotations

import subprocess
from dataclasses import replace
from pathlib import Path

from mini_runbot.config import Settings
from mini_runbot.domain.errors import GitOperationError, UnsafePathError
from mini_runbot.domain.models import RepositoryRevision


class GitCliService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def checkout(
        self,
        revision: RepositoryRevision,
        workspace_path: Path,
        log_path: Path,
    ) -> RepositoryRevision:
        config = self.settings.repository(revision.name, revision.requested_ref)
        source = Path(config.url).expanduser().resolve()
        if not source.is_dir():
            raise GitOperationError(f"Configured repository does not exist: {source}")
        source_check = self._run(
            ["git", "-C", str(source), "rev-parse", "--is-inside-work-tree"]
        )
        if source_check.strip() != "true":
            raise GitOperationError(f"Configured source is not a Git repository: {source}")

        sha = self._run(
            [
                "git",
                "-C",
                str(source),
                "rev-parse",
                "--verify",
                f"{revision.requested_ref}^{{commit}}",
            ]
        ).strip()
        sources_root = (workspace_path / "sources").resolve()
        target = (sources_root / config.target).resolve()
        if target.parent != sources_root:
            raise UnsafePathError(f"Checkout target escaped sources directory: {target}")
        if target.exists():
            raise GitOperationError(f"Checkout target already exists: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)

        log_path.parent.mkdir(parents=True, exist_ok=True)
        output = self._run(["git", "clone", "--no-checkout", "--", str(source), str(target)])
        output += self._run(["git", "-C", str(target), "checkout", "--detach", sha])
        log_path.write_text(output, encoding="utf-8")
        addons_path = (target / config.addons_subpath).resolve()
        if target not in {addons_path, *addons_path.parents} or not addons_path.is_dir():
            raise GitOperationError(
                f"Configured addons_subpath does not exist inside checkout: {config.addons_subpath}"
            )
        return replace(
            revision,
            source=str(source),
            commit_sha=sha,
            checkout_path=str(addons_path),
            addons_priority=config.addons_priority,
        )

    @staticmethod
    def _run(arguments: list[str]) -> str:
        try:
            result = subprocess.run(
                arguments, capture_output=True, text=True, timeout=120, check=False
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise GitOperationError(f"Git command could not run: {exc}") from exc
        output = f"{result.stdout}{result.stderr}"
        if result.returncode != 0:
            safe_command = " ".join(arguments[:3])
            raise GitOperationError(f"Git command failed ({safe_command}): {output[-500:]}")
        return output
