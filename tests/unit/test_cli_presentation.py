from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path

from rich.console import Console

from mini_runbot.cli.presentation import print_build, print_build_list
from mini_runbot.domain.enums import BuildStatus, StageStatus
from mini_runbot.domain.models import Build, RepositoryRevision, StageResult


def _build() -> Build:
    now = datetime.now(UTC)
    return Build(
        id="build-20260919-example",
        status=BuildStatus.RUNNING,
        requested_ref="feature/dashboard",
        repositories=[
            RepositoryRevision(
                name="custom",
                source="custom",
                requested_ref="feature/dashboard",
                commit_sha="a" * 40,
            )
        ],
        modules=["custom_sale"],
        created_at=now,
        started_at=now,
        expires_at=now + timedelta(hours=4),
        workspace_path=Path("builds/build-20260919-example"),
        compose_project_name="build_20260919_example",
        database_name="build_20260919_example",
        host_port=18123,
        preview_url="http://127.0.0.1:18123",
        stages=[
            StageResult(
                name="install",
                status=StageStatus.SUCCESS,
                duration_seconds=12.4,
                summary="install passed",
            )
        ],
    )


def test_build_detail_renders_human_readable_pipeline() -> None:
    output = StringIO()
    console = Console(file=output, force_terminal=False, width=120)

    print_build(_build(), console)

    rendered = output.getvalue()
    assert "build-20260919-example" in rendered
    assert "RUNNING" in rendered
    assert "Resolved repositories" in rendered
    assert "Pipeline" in rendered
    assert "install passed" in rendered


def test_build_list_renders_status_ref_and_preview() -> None:
    output = StringIO()
    console = Console(file=output, force_terminal=False, width=180)

    print_build_list([_build()], console)

    rendered = output.getvalue()
    assert "Mini-Runbot builds (1)" in rendered
    assert "feature/dashboard" in rendered
    assert "http://127.0.0.1:18123" in rendered


def test_json_output_remains_machine_readable() -> None:
    output = StringIO()
    console = Console(file=output, force_terminal=False)

    print_build(_build(), console, json_output=True)

    assert '"id": "build-20260919-example"' in output.getvalue()
