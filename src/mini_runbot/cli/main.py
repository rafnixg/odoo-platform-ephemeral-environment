import json
import platform
import shutil
import subprocess
from typing import Annotated

import typer

from mini_runbot.api.schemas import BuildResponse
from mini_runbot.bootstrap import create_manager
from mini_runbot.config import Settings
from mini_runbot.domain.errors import BuildNotFoundError, MiniRunbotError
from mini_runbot.domain.validation import CreateBuildRequest

app = typer.Typer(help="Local Mini-Runbot proof of concept.")
build_app = typer.Typer(help="Manage builds.")
app.add_typer(build_app, name="build")


def _print_build(build: object) -> None:
    response = BuildResponse.from_domain(build)  # type: ignore[arg-type]
    typer.echo(json.dumps(response.model_dump(mode="json"), indent=2))


@build_app.command("create")
def create_build(
    repo: Annotated[str, typer.Option("--repo")],
    ref: Annotated[str, typer.Option("--ref")],
    modules: Annotated[str, typer.Option("--modules")],
    ttl_seconds: Annotated[int, typer.Option("--ttl-seconds")] = 14_400,
) -> None:
    request = CreateBuildRequest(
        repository=repo,
        ref=ref,
        modules=[item.strip() for item in modules.split(",") if item.strip()],
        ttl_seconds=ttl_seconds,
    )
    _print_build(create_manager().create(request))


@build_app.command("get")
def get_build(build_id: str) -> None:
    try:
        _print_build(create_manager().get(build_id))
    except BuildNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc


@build_app.command("list")
def list_builds() -> None:
    builds = [
        BuildResponse.from_domain(item).model_dump(mode="json")
        for item in create_manager().list()
    ]
    typer.echo(json.dumps(builds, indent=2))


@build_app.command("destroy")
def destroy_build(build_id: str) -> None:
    try:
        _print_build(create_manager().destroy(build_id))
    except MiniRunbotError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc


def _command_version(arguments: list[str]) -> tuple[bool, str]:
    try:
        result = subprocess.run(arguments, capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    output = (result.stdout or result.stderr).strip().splitlines()
    return result.returncode == 0, output[0] if output else f"exit code {result.returncode}"


@app.command("doctor")
def doctor() -> None:
    settings = Settings.from_environment()
    checks: list[tuple[str, bool, str]] = []
    python_ok = tuple(map(int, platform.python_version_tuple()[:2])) >= (3, 12)
    checks.append(("python", python_ok, platform.python_version()))
    checks.append(("git", *_command_version(["git", "--version"])))
    checks.append(("docker", *_command_version(["docker", "--version"])))
    checks.append(("compose", *_command_version(["docker", "compose", "version"])))
    checks.append(
        (
            "docker-daemon",
            *_command_version(["docker", "info", "--format", "{{.ServerVersion}}"]),
        )
    )
    root = settings.builds_root.resolve()
    parent = root if root.exists() else root.parent
    checks.append(("builds-root", parent.exists() and parent.is_dir(), str(root)))
    git_path = shutil.which("git")
    checks.append(("git-executable", git_path is not None, git_path or "not found"))
    for name, ok, detail in checks:
        typer.echo(f"[{'OK' if ok else 'FAIL'}] {name}: {detail}")
    if not all(ok for _, ok, _ in checks):
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
