import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from mini_runbot.adapters.runtime.compose import DockerComposeRuntimeService
from mini_runbot.config import Settings
from mini_runbot.domain.enums import BuildStatus
from mini_runbot.domain.models import Build, RepositoryRevision


def test_render_uses_isolated_names_port_and_read_only_mount(tmp_path: Path) -> None:
    root = tmp_path / "builds"
    workspace = root / "build-safe"
    checkout = workspace / "sources" / "custom"
    checkout.mkdir(parents=True)
    now = datetime.now(UTC)
    build = Build(
        id="build-safe",
        status=BuildStatus.PREPARING,
        requested_ref="HEAD",
        repositories=[
            RepositoryRevision(
                name="custom",
                source=str(checkout),
                requested_ref="HEAD",
                commit_sha="a" * 40,
                checkout_path=str(checkout),
            )
        ],
        modules=["demo_module"],
        created_at=now,
        expires_at=now + timedelta(hours=1),
        workspace_path=workspace,
        compose_project_name="build_safe",
        database_name="build_safe",
        host_port=18123,
        preview_url="http://127.0.0.1:18123",
    )
    runtime = DockerComposeRuntimeService(Settings(builds_root=root))
    runtime.prepare(build.id, workspace)

    result = runtime.render(build)
    rendered = (workspace / "runtime" / "compose.yaml").read_text(encoding="utf-8")

    assert result.exit_code == 0
    assert "127.0.0.1:18123:8069" in rendered
    assert "build_safe" in rendered
    assert "--db_host=db" in rendered
    assert "--database_host" not in rendered
    assert f"{checkout.as_posix()}:/mnt/addons/custom:ro" in rendered.replace("\\\\", "/")
    assert "/var/run/docker.sock" not in rendered


def test_addons_path_orders_multiple_repositories_by_priority(tmp_path: Path) -> None:
    root = tmp_path / "builds"
    workspace = root / "build-multi"
    oca = workspace / "sources" / "oca"
    custom = workspace / "sources" / "custom"
    oca.mkdir(parents=True)
    custom.mkdir()
    now = datetime.now(UTC)
    build = Build(
        id="build-multi",
        status=BuildStatus.PREPARING,
        requested_ref="16.0",
        repositories=[
            RepositoryRevision(
                name="oca",
                source=str(oca),
                requested_ref="16.0",
                commit_sha="a" * 40,
                checkout_path=str(oca),
                addons_priority=200,
            ),
            RepositoryRevision(
                name="custom",
                source=str(custom),
                requested_ref="feature/multi",
                commit_sha="b" * 40,
                checkout_path=str(custom),
                addons_priority=100,
            ),
        ],
        modules=["demo_module"],
        created_at=now,
        expires_at=now + timedelta(hours=1),
        workspace_path=workspace,
        compose_project_name="build_multi",
        database_name="build_multi",
        host_port=18124,
    )
    runtime = DockerComposeRuntimeService(Settings(builds_root=root))
    runtime.prepare(build.id, workspace)

    runtime.render(build)

    rendered = (workspace / "runtime" / "compose.yaml").read_text(encoding="utf-8")
    assert rendered.index("/mnt/addons/custom") < rendered.index("/mnt/addons/oca")
    assert DockerComposeRuntimeService._addons_path(build).endswith(
        "/mnt/addons/custom,/mnt/addons/oca"
    )


def test_parse_compose_ps_supports_array_and_json_lines() -> None:
    entries = [
        {"Service": "db", "State": "running", "Health": "healthy"},
        {"Service": "odoo", "State": "running", "Health": ""},
    ]

    assert DockerComposeRuntimeService._parse_compose_ps(json.dumps(entries)) == entries
    assert DockerComposeRuntimeService._parse_compose_ps(
        "\n".join(json.dumps(item) for item in entries)
    ) == entries
