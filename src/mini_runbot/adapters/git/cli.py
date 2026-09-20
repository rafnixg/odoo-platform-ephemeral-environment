from __future__ import annotations

import subprocess
from dataclasses import replace
from pathlib import Path
from urllib.parse import urlsplit

from mini_runbot.config import Settings
from mini_runbot.domain.errors import GitOperationError, UnsafePathError
from mini_runbot.domain.models import RepositoryRevision

REMOTE_GIT_SCHEMES = {"https", "ssh"}


def is_remote_git_url(value: str) -> bool:
    """Return whether a configured source is an allowed remote Git URL."""
    parsed = urlsplit(value)
    if parsed.scheme.lower() in REMOTE_GIT_SCHEMES:
        return True
    return value.startswith("git@") and ":" in value.partition("@")[2]


def validate_remote_git_url(value: str) -> None:
    parsed = urlsplit(value)
    if parsed.scheme:
        if parsed.scheme.lower() not in REMOTE_GIT_SCHEMES:
            raise GitOperationError(
                "Remote repository URL must use HTTPS or SSH"
            )
        if not parsed.hostname:
            raise GitOperationError("Remote repository URL must include a host")
        if parsed.scheme.lower() == "https" and (parsed.username or parsed.password):
            raise GitOperationError(
                "HTTPS repository URLs must not contain embedded credentials"
            )
        if parsed.password:
            raise GitOperationError(
                "SSH repository URLs must not contain an embedded password"
            )
        return
    if value.startswith("git@") and ":" in value.partition("@")[2]:
        return
    raise GitOperationError("Remote repository URL must use HTTPS or SSH")


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
        sources_root = (workspace_path / "sources").resolve()
        target = (sources_root / config.target).resolve()
        if target.parent != sources_root:
            raise UnsafePathError(f"Checkout target escaped sources directory: {target}")
        if target.exists():
            raise GitOperationError(f"Checkout target already exists: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)

        log_path.parent.mkdir(parents=True, exist_ok=True)
        if is_remote_git_url(config.url) or "://" in config.url:
            source = config.url
            sha, output = self._checkout_remote(source, revision.requested_ref, target)
        else:
            source_path = Path(config.url).expanduser().resolve()
            if not source_path.is_dir():
                raise GitOperationError(
                    f"Configured repository does not exist: {source_path}"
                )
            source_check = self._run(
                ["git", "-C", str(source_path), "rev-parse", "--is-inside-work-tree"]
            )
            if source_check.strip() != "true":
                raise GitOperationError(
                    f"Configured source is not a Git repository: {source_path}"
                )
            sha = self._run(
                [
                    "git",
                    "-C",
                    str(source_path),
                    "rev-parse",
                    "--verify",
                    f"{revision.requested_ref}^{{commit}}",
                ]
            ).strip()
            output = self._run(
                ["git", "clone", "--no-checkout", "--", str(source_path), str(target)]
            )
            output += self._run(
                ["git", "-C", str(target), "checkout", "--detach", sha]
            )
            source = str(source_path)
        log_path.write_text(output, encoding="utf-8")
        addons_path = (target / config.addons_subpath).resolve()
        if target not in {addons_path, *addons_path.parents} or not addons_path.is_dir():
            raise GitOperationError(
                f"Configured addons_subpath does not exist inside checkout: {config.addons_subpath}"
            )
        return replace(
            revision,
            source=source,
            commit_sha=sha,
            checkout_path=str(addons_path),
            addons_priority=config.addons_priority,
        )

    def _checkout_remote(
        self, source: str, requested_ref: str, target: Path
    ) -> tuple[str, str]:
        validate_remote_git_url(source)
        target.mkdir()
        output = self._run(["git", "init", str(target)])
        output += self._run(
            ["git", "-C", str(target), "remote", "add", "origin", source]
        )
        output += self._run(
            [
                "git",
                "-C",
                str(target),
                "fetch",
                "--depth=1",
                "--no-tags",
                "origin",
                requested_ref,
            ]
        )
        sha = self._run(
            [
                "git",
                "-C",
                str(target),
                "rev-parse",
                "--verify",
                "FETCH_HEAD^{commit}",
            ]
        ).strip()
        output += self._run(
            ["git", "-C", str(target), "checkout", "--detach", sha]
        )
        return sha, output

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
