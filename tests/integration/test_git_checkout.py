import subprocess
from pathlib import Path

from mini_runbot.adapters.git.cli import GitCliService
from mini_runbot.config import RepositoryConfig, Settings
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
