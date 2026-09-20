import subprocess
from pathlib import Path

import pytest

from mini_runbot.adapters.git.cli import GitCliService
from mini_runbot.config import RepositoryConfig, Settings
from mini_runbot.domain.errors import GitOperationError
from mini_runbot.domain.models import RepositoryRevision


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def test_resolves_sha_and_creates_detached_isolated_checkout(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _git(source, "init")
    _git(source, "config", "user.name", "Test")
    _git(source, "config", "user.email", "test@example.invalid")
    (source / "README.md").write_text("fixture", encoding="utf-8")
    _git(source, "add", "README.md")
    _git(source, "commit", "-m", "fixture")
    sha = _git(source, "rev-parse", "HEAD")

    workspace = tmp_path / "builds" / "build-test"
    settings = Settings(
        builds_root=tmp_path / "builds",
        repositories={"custom": RepositoryConfig(url=str(source), target="custom-addons")},
    )
    service = GitCliService(settings)
    revision = service.checkout(
        RepositoryRevision(name="custom", source=str(source), requested_ref="HEAD"),
        workspace,
        workspace / "logs" / "checkout.log",
    )

    checkout = Path(revision.checkout_path or "")
    assert revision.commit_sha == sha
    assert _git(checkout, "rev-parse", "HEAD") == sha
    assert _git(checkout, "rev-parse", "--abbrev-ref", "HEAD") == "HEAD"
    assert (source / ".git").is_dir()


def test_fetches_remote_ref_and_checks_out_immutable_sha(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = tmp_path / "builds" / "build-remote"
    remote_url = "https://github.com/OCA/e-commerce.git"
    settings = Settings(
        builds_root=tmp_path / "builds",
        repositories={
            "custom": RepositoryConfig(url=remote_url, target="custom-addons")
        },
    )
    service = GitCliService(settings)
    sha = "a" * 40
    commands: list[list[str]] = []

    def fake_run(arguments: list[str]) -> str:
        commands.append(arguments)
        if "rev-parse" in arguments:
            return f"{sha}\n"
        return "ok\n"

    monkeypatch.setattr(service, "_run", fake_run)
    revision = service.checkout(
        RepositoryRevision(name="custom", source=remote_url, requested_ref="16.0"),
        workspace,
        workspace / "logs" / "checkout.log",
    )

    checkout = Path(revision.checkout_path or "")
    assert revision.source == remote_url
    assert revision.commit_sha == sha
    assert checkout == (workspace / "sources" / "custom-addons").resolve()
    assert any(
        command[-4:] == ["--depth=1", "--no-tags", "origin", "16.0"]
        for command in commands
        if "fetch" in command
    )
    assert ["checkout", "--detach", sha] == commands[-1][-3:]


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/OCA/e-commerce.git",
        "https://token@github.com/OCA/e-commerce.git",
        "file:///tmp/e-commerce.git",
    ],
)
def test_rejects_unsafe_remote_urls(tmp_path: Path, url: str) -> None:
    workspace = tmp_path / "builds" / "build-unsafe"
    settings = Settings(
        builds_root=tmp_path / "builds",
        repositories={"custom": RepositoryConfig(url=url, target="custom-addons")},
    )

    with pytest.raises(GitOperationError):
        GitCliService(settings).checkout(
            RepositoryRevision(name="custom", source=url, requested_ref="16.0"),
            workspace,
            workspace / "logs" / "checkout.log",
        )
