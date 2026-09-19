import json
import platform
import shutil
import subprocess
from pathlib import Path
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
    run: Annotated[bool, typer.Option("--run", help="Execute immediately with Docker.")] = False,
) -> None:
    request = CreateBuildRequest(
        repository=repo,
        ref=ref,
        modules=[item.strip() for item in modules.split(",") if item.strip()],
        ttl_seconds=ttl_seconds,
    )
    manager = create_manager(docker=run)
    build = manager.create(request)
    if run:
        build = manager.execute(build.id)
    _print_build(build)


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


@build_app.command("run")
def run_build(build_id: str) -> None:
    try:
        _print_build(create_manager(docker=True).execute(build_id))
    except MiniRunbotError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc


@build_app.command("logs")
def build_logs(
    build_id: str,
    stage: Annotated[str | None, typer.Option("--stage")] = None,
) -> None:
    try:
        build = create_manager().get(build_id)
    except BuildNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    selected = [item for item in build.stages if stage is None or item.name == stage]
    if not selected:
        typer.echo("No matching stage logs", err=True)
        raise typer.Exit(1)
    for item in selected:
        typer.echo(f"== {item.name} ({item.status}) ==")
        if item.log_path and Path(item.log_path).is_file():
            typer.echo(Path(item.log_path).read_text(encoding="utf-8", errors="replace"))
        else:
            typer.echo(item.summary or "No log file recorded")


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
    for alias, repository in settings.repositories.items():
        repository_path = Path(repository.url).expanduser().resolve()
        exists = repository_path.is_dir()
        checks.append((f"repository-{alias}", exists, str(repository_path)))
        if exists:
            ok, detail = _command_version(
                ["git", "-C", str(repository_path), "rev-parse", "--is-inside-work-tree"]
            )
            checks.append((f"repository-{alias}-git", ok and detail == "true", detail))
    for name, ok, detail in checks:
        typer.echo(f"[{'OK' if ok else 'FAIL'}] {name}: {detail}")
    if not all(ok for _, ok, _ in checks):
        raise typer.Exit(1)


@app.command("cleanup")
def cleanup(
    expired: Annotated[bool, typer.Option("--expired", help="Destroy expired builds.")] = False,
) -> None:
    if not expired:
        typer.echo("Specify --expired", err=True)
        raise typer.Exit(2)
    result = create_manager(docker=True).cleanup_expired()
    typer.echo(
        json.dumps(
            {
                "examined": result.examined,
                "destroyed_ids": result.destroyed_ids,
                "failed_ids": result.failed_ids,
            },
            indent=2,
        )
    )


@app.command("recover")
def recover() -> None:
    """Classify interrupted builds after a confirmed orchestrator restart."""
    result = create_manager(docker=True).recover_interrupted()
    typer.echo(
        json.dumps(
            {
                "examined": result.examined,
                "recovered_ids": result.destroyed_ids,
                "failed_ids": result.failed_ids,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    app()
