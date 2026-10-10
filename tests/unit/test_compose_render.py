import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from mini_runbot.adapters.runtime.compose import DockerComposeRuntimeService
from mini_runbot.config import Settings
from mini_runbot.domain.enums import BuildStatus
from mini_runbot.domain.errors import RuntimeOperationError
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
    assert "--http-interface=0.0.0.0" in rendered
    assert f"{checkout.as_posix()}:/mnt/addons/custom:ro" in rendered.replace("\\\\", "/")
    assert "odoo-data:/var/lib/odoo" in rendered
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


@pytest.mark.parametrize(
    ("series", "load_demo_data", "expected_flag"),
    [
        ((16, 0), True, None),
        ((16, 0), False, "--without-demo=all"),
        ((18, 0), False, "--without-demo=all"),
        ((19, 0), True, "--with-demo"),
        ((19, 0), False, None),
        ((20, 0), True, "--with-demo"),
        (None, True, None),
        (None, False, "--without-demo=all"),
    ],
)
def test_install_demo_data_flag_follows_the_odoo_series(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    series: tuple[int, int] | None,
    load_demo_data: bool,
    expected_flag: str | None,
) -> None:
    runtime = DockerComposeRuntimeService(
        Settings(builds_root=tmp_path, load_demo_data=load_demo_data)
    )
    captured: list[str] = []

    def fake_run(build, stage: str, arguments: list[str]):
        captured.extend(arguments)
        return None

    monkeypatch.setattr(runtime, "_run", fake_run)
    monkeypatch.setattr(runtime, "_odoo_series", lambda build: series)
    monkeypatch.setattr(runtime, "_verify_installed", lambda build: None)
    build = SimpleNamespace(
        database_name="demo",
        modules=["demo_module"],
        repositories=[],
    )

    runtime.install_modules(build)  # type: ignore[arg-type]

    demo_flags = [item for item in captured if "demo" in item and item.startswith("--")]
    assert demo_flags == ([expected_flag] if expected_flag else [])


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        ("Odoo Server 16.0-20250909\n", (16, 0)),
        ("Odoo Server 20.0-20260926\n", (20, 0)),
        ("Odoo Server saas~18.2\n", (18, 2)),
    ],
)
def test_odoo_series_is_parsed_from_the_image_banner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    output: str,
    expected: tuple[int, int],
) -> None:
    runtime = DockerComposeRuntimeService(Settings(builds_root=tmp_path))
    monkeypatch.setattr(runtime, "_execute", lambda build, stage, arguments: (None, output))

    assert runtime._odoo_series(SimpleNamespace()) == expected  # type: ignore[arg-type]


def test_odoo_series_rejects_unrecognized_banner_with_log_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = DockerComposeRuntimeService(Settings(builds_root=tmp_path))
    monkeypatch.setattr(
        runtime,
        "_execute",
        lambda build, stage, arguments: (
            SimpleNamespace(log_path="odoo_version.log"),
            "unexpected banner\n",
        ),
    )

    with pytest.raises(
        RuntimeOperationError, match="Could not determine the Odoo series"
    ) as raised:
        runtime._odoo_series(SimpleNamespace())  # type: ignore[arg-type]

    assert raised.value.log_path == "odoo_version.log"


def _verification_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, output: str
) -> tuple[DockerComposeRuntimeService, list[str]]:
    runtime = DockerComposeRuntimeService(Settings(builds_root=tmp_path))
    captured: list[str] = []

    def fake_execute(build, stage: str, arguments: list[str]):
        captured.extend(arguments)
        return SimpleNamespace(log_path="install_verify.log"), output

    monkeypatch.setattr(runtime, "_execute", fake_execute)
    return runtime, captured


def test_install_verification_accepts_installed_modules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime, captured = _verification_runtime(
        tmp_path, monkeypatch, "module_a|installed\nmodule_b|installed\n"
    )
    build = SimpleNamespace(database_name="demo", modules=["module_a", "module_b"])

    runtime._verify_installed(build)  # type: ignore[arg-type]

    assert captured[:3] == ["exec", "-T", "db"]
    assert "'module_a', 'module_b'" in captured[-1]


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        ("module_a|installed\nmodule_b|uninstallable\n", "module_b (uninstallable)"),
        ("module_a|installed\n", "module_b (not found)"),
    ],
)
def test_install_verification_rejects_skipped_modules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, output: str, expected: str
) -> None:
    runtime, _ = _verification_runtime(tmp_path, monkeypatch, output)
    build = SimpleNamespace(database_name="demo", modules=["module_a", "module_b"])

    with pytest.raises(RuntimeOperationError, match="not installed") as raised:
        runtime._verify_installed(build)  # type: ignore[arg-type]

    assert expected in str(raised.value)
    assert raised.value.log_path == "install_verify.log"


def test_install_verification_never_interpolates_unsafe_module_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime, captured = _verification_runtime(tmp_path, monkeypatch, "")
    build = SimpleNamespace(database_name="demo", modules=["module_a'; DROP TABLE x; --"])

    with pytest.raises(RuntimeOperationError, match="cannot be verified"):
        runtime._verify_installed(build)  # type: ignore[arg-type]

    assert captured == []
