import platform
import shutil
import subprocess
from pathlib import Path
from typing import Annotated

import typer
import uvicorn
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from mini_runbot.adapters.git.cli import is_remote_git_url, validate_remote_git_url
from mini_runbot.bootstrap import create_manager
from mini_runbot.cli.init_config import (
    collect_config,
    load_example_config,
    render_config,
    write_config_exclusive,
)
from mini_runbot.cli.presentation import print_build, print_build_list, print_operation_result
from mini_runbot.config import Settings
from mini_runbot.domain.errors import BuildNotFoundError, MiniRunbotError
from mini_runbot.domain.validation import CreateBuildRequest, RequestedRepository

app = typer.Typer(help="Local Mini-Runbot proof of concept.")
build_app = typer.Typer(help="Manage builds.")
app.add_typer(build_app, name="build")
console = Console()


@app.command("init")
def init_config(
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Configuration file to create.",
            dir_okay=False,
        ),
    ] = Path("config.local.yaml"),
    defaults: Annotated[
        bool,
        typer.Option(
            "--defaults",
            help="Create the file from bundled defaults without interactive prompts.",
        ),
    ] = False,
) -> None:
    """Create a local configuration without overwriting an existing file."""
    destination = output.expanduser().resolve()
    if destination.exists():
        typer.echo(f"Configuration already exists: {destination}", err=True)
        raise typer.Exit(1)
    config = load_example_config()
    if not defaults:
        config = collect_config(config)
    try:
        created = write_config_exclusive(destination, render_config(config))
    except (FileExistsError, OSError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Created configuration: {created}")
    typer.echo("PowerShell:")
    typer.echo(f"  $env:MINI_RUNBOT_CONFIG = '{created}'")
    typer.echo("Bash:")
    typer.echo(f"  export MINI_RUNBOT_CONFIG='{created.as_posix()}'")
    typer.echo("Next: mini-runbot doctor")


@build_app.command("create")
def create_build(
    repo: Annotated[str, typer.Option("--repo")],
    ref: Annotated[str, typer.Option("--ref")],
    modules: Annotated[str, typer.Option("--modules")],
    extra_repo: Annotated[
        list[str] | None,
        typer.Option(
            "--extra-repo",
            help="Additional configured repository as ALIAS=REF; repeat as needed.",
        ),
    ] = None,
    ttl_seconds: Annotated[int, typer.Option("--ttl-seconds")] = 14_400,
    run: Annotated[bool, typer.Option("--run", help="Execute immediately with Docker.")] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="Emit machine-readable JSON.")
    ] = False,
) -> None:
    try:
        repositories = [RequestedRepository(repository=repo, ref=ref)]
        for value in extra_repo or []:
            alias, separator, extra_ref = value.partition("=")
            if not separator or not alias or not extra_ref:
                raise typer.BadParameter(
                    "additional repositories must use ALIAS=REF",
                    param_hint="--extra-repo",
                )
            repositories.append(RequestedRepository(repository=alias, ref=extra_ref))
        request = CreateBuildRequest(
            repositories=repositories,
            modules=[item.strip() for item in modules.split(",") if item.strip()],
            ttl_seconds=ttl_seconds,
        )
    except ValidationError as exc:
        message = exc.errors(include_url=False)[0]["msg"]
        raise typer.BadParameter(str(message)) from exc
    try:
        manager = create_manager(docker=run)
        build = manager.create(request)
        if run:
            build = manager.execute(build.id)
        print_build(build, console, json_output=json_output)
    except MiniRunbotError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc


@build_app.command("get")
def get_build(
    build_id: str,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    try:
        print_build(create_manager().get(build_id), console, json_output=json_output)
    except BuildNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc


@build_app.command("list")
def list_builds(
    status: Annotated[str | None, typer.Option("--status", help="Filter by build status.")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    builds = create_manager().list()
    if status:
        builds = [item for item in builds if item.status.value == status.lower()]
    print_build_list(builds, console, json_output=json_output)


@build_app.command("destroy")
def destroy_build(
    build_id: str,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    try:
        print_build(
            create_manager(docker=True).destroy(build_id),
            console,
            json_output=json_output,
        )
    except MiniRunbotError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc


@build_app.command("run")
def run_build(
    build_id: str,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    try:
        print_build(
            create_manager(docker=True).execute(build_id),
            console,
            json_output=json_output,
        )
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
        console.rule(f"[bold]{item.name}[/bold] · {item.status.value}")
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
        if is_remote_git_url(repository.url) or "://" in repository.url:
            try:
                validate_remote_git_url(repository.url)
            except MiniRunbotError as exc:
                checks.append((f"repository-{alias}-remote", False, str(exc)))
                continue
            ok, detail = _command_version(
                [
                    "git",
                    "ls-remote",
                    "--exit-code",
                    repository.url,
                    repository.default_ref,
                ]
            )
            checks.append((f"repository-{alias}-remote", ok, detail))
        else:
            repository_path = Path(repository.url).expanduser().resolve()
            exists = repository_path.is_dir()
            checks.append((f"repository-{alias}", exists, str(repository_path)))
            if exists:
                ok, detail = _command_version(
                    [
                        "git",
                        "-C",
                        str(repository_path),
                        "rev-parse",
                        "--is-inside-work-tree",
                    ]
                )
                checks.append((f"repository-{alias}-git", ok and detail == "true", detail))
    table = Table(title="Mini-Runbot doctor", header_style="bold dim")
    table.add_column("Check")
    table.add_column("Result")
    table.add_column("Detail", overflow="fold")
    for name, ok, detail in checks:
        table.add_row(name, "[green]OK[/green]" if ok else "[red]FAIL[/red]", detail)
    console.print(table)
    if not all(ok for _, ok, _ in checks):
        raise typer.Exit(1)


@app.command("serve")
def serve(
    host: Annotated[str, typer.Option("--host")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", min=1, max=65535)] = 8000,
    reload: Annotated[bool, typer.Option("--reload")] = False,
) -> None:
    """Serve the API and dashboard from one process."""
    console.print(f"[bold green]Mini-Runbot[/bold green] → http://{host}:{port}")
    uvicorn.run("mini_runbot.api.app:app", host=host, port=port, reload=reload)


@app.command("cleanup")
def cleanup(
    expired: Annotated[bool, typer.Option("--expired", help="Destroy expired builds.")] = False,
    retained: Annotated[
        bool,
        typer.Option(
            "--retained",
            help="Purge destroyed builds older than the configured retention period.",
        ),
    ] = False,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    if not expired and not retained:
        typer.echo("Specify --expired and/or --retained", err=True)
        raise typer.Exit(2)
    manager = create_manager(docker=True)
    payload: dict[str, object] = {}
    if expired:
        result = manager.cleanup_expired()
        expired_result = {
            "examined": result.examined,
            "destroyed_ids": result.destroyed_ids,
            "failed_ids": result.failed_ids,
        }
        payload["expired"] = expired_result
        if not json_output:
            print_operation_result("Expired build cleanup", expired_result, console)
    if retained:
        purge = manager.purge_destroyed()
        retained_result = {
            "examined": purge.examined,
            "purged_ids": purge.purged_ids,
            "failed_ids": purge.failed_ids,
        }
        payload["retained"] = retained_result
        if not json_output:
            print_operation_result(
                "Destroyed build retention cleanup", retained_result, console
            )
    if json_output:
        print_operation_result(
            "Cleanup",
            payload,
            console,
            json_output=True,
        )


@app.command("recover")
def recover(
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Classify interrupted builds after a confirmed orchestrator restart."""
    result = create_manager(docker=True).recover_interrupted()
    print_operation_result(
        "Interrupted build recovery",
        {
            "examined": result.examined,
            "recovered_ids": result.destroyed_ids,
            "failed_ids": result.failed_ids,
        },
        console,
        json_output=json_output,
    )


if __name__ == "__main__":
    app()
