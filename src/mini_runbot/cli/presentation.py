import json
from collections.abc import Iterable
from datetime import UTC, datetime

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from mini_runbot.api.schemas import BuildResponse
from mini_runbot.domain.enums import BuildStatus, StageStatus
from mini_runbot.domain.models import Build

STATUS_STYLE = {
    BuildStatus.RUNNING: "bold green",
    BuildStatus.FAILED: "bold red",
    BuildStatus.DESTROYED: "dim",
    BuildStatus.EXPIRED: "yellow",
    BuildStatus.NEW: "cyan",
    BuildStatus.CHECKING_OUT: "yellow",
    BuildStatus.PREPARING: "yellow",
    BuildStatus.INSTALLING: "yellow",
    BuildStatus.TESTING: "yellow",
    BuildStatus.STARTING: "yellow",
    BuildStatus.DESTROYING: "yellow",
}


def _print_json(payload: object, console: Console) -> None:
    console.print(json.dumps(payload, indent=2), markup=False, highlight=False, soft_wrap=True)


def _status(status: BuildStatus) -> Text:
    return Text(status.value.replace("_", " ").upper(), style=STATUS_STYLE[status])


def _when(value: datetime | None) -> str:
    if value is None:
        return "—"
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def _duration(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    if seconds < 1:
        return f"{seconds * 1000:.0f} ms"
    if seconds < 60:
        return f"{seconds:.1f} s"
    return f"{int(seconds // 60)}m {seconds % 60:.0f}s"


def print_build(build: Build, console: Console, *, json_output: bool = False) -> None:
    response = BuildResponse.from_domain(build)
    if json_output:
        _print_json(response.model_dump(mode="json"), console)
        return

    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="dim", width=16)
    summary.add_column()
    summary.add_row("Status", _status(build.status))
    summary.add_row("Reference", build.requested_ref)
    summary.add_row("Modules", ", ".join(build.modules))
    summary.add_row("Created", _when(build.created_at))
    summary.add_row("Expires", _when(build.expires_at))
    summary.add_row("Preview", build.preview_url or "—")
    if build.failure_message:
        summary.add_row("Failure stage", build.failure_stage or "—")
        summary.add_row("Failure", Text(build.failure_message, style="red"))

    revisions = Table(title="Resolved repositories", box=None, header_style="bold dim")
    revisions.add_column("Alias")
    revisions.add_column("Requested ref")
    revisions.add_column("Commit SHA", style="cyan", overflow="fold")
    for revision in build.repositories:
        revisions.add_row(
            revision.name,
            revision.requested_ref,
            revision.commit_sha or "pending",
        )

    stages = Table(title="Pipeline", box=None, header_style="bold dim")
    stages.add_column("Stage")
    stages.add_column("Result")
    stages.add_column("Duration", justify="right")
    stages.add_column("Summary", overflow="fold")
    for stage in build.stages:
        style = "green" if stage.status == StageStatus.SUCCESS else "red"
        stages.add_row(
            stage.name.replace("_", " "),
            Text(stage.status.value.upper(), style=style),
            _duration(stage.duration_seconds),
            stage.summary or "—",
        )
    if not build.stages:
        stages.add_row("—", "PENDING", "—", "Waiting for execution")

    console.print(
        Panel(
            Group(summary, Text(), revisions, Text(), stages),
            title=f"[bold]{build.id}[/bold]",
            border_style=STATUS_STYLE[build.status].split()[-1],
            padding=(1, 2),
        )
    )


def print_build_list(
    builds: Iterable[Build], console: Console, *, json_output: bool = False
) -> None:
    items = list(builds)
    if json_output:
        payload = [BuildResponse.from_domain(item).model_dump(mode="json") for item in items]
        _print_json(payload, console)
        return

    table = Table(
        title=f"Mini-Runbot builds ({len(items)})",
        header_style="bold dim",
        show_lines=False,
    )
    table.add_column("Build", style="bold")
    table.add_column("Status")
    table.add_column("Reference")
    table.add_column("Modules", overflow="ellipsis")
    table.add_column("SHA", style="cyan")
    table.add_column("Created")
    table.add_column("Preview")
    for build in items:
        sha = build.repositories[0].commit_sha if build.repositories else None
        table.add_row(
            build.id,
            _status(build.status),
            build.requested_ref,
            ", ".join(build.modules),
            sha[:10] if sha else "pending",
            _when(build.created_at),
            build.preview_url or "—",
        )
    if not items:
        table.add_row("No builds recorded", "—", "—", "—", "—", "—", "—")
    console.print(table)


def print_operation_result(
    title: str,
    values: dict[str, object],
    console: Console,
    *,
    json_output: bool = False,
) -> None:
    if json_output:
        _print_json(values, console)
        return
    table = Table.grid(padding=(0, 2))
    table.add_column(style="dim")
    table.add_column()
    for key, value in values.items():
        if isinstance(value, list):
            rendered = ", ".join(str(item) for item in value) or "—"
        else:
            rendered = str(value)
        table.add_row(key.replace("_", " ").title(), rendered)
    console.print(Panel(table, title=title, border_style="cyan"))
