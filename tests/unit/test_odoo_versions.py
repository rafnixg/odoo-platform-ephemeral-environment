from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from mini_runbot.adapters.persistence.sqlite import SqliteBuildRepository
from mini_runbot.adapters.runtime.compose import DockerComposeRuntimeService
from mini_runbot.config import OdooVersionConfig, RepositoryConfig, Settings
from mini_runbot.domain.enums import BuildStatus
from mini_runbot.domain.errors import ConfigurationError
from mini_runbot.domain.models import Build, RepositoryRevision
from mini_runbot.domain.validation import CreateBuildRequest


def _settings_with_versions() -> Settings:
    return Settings(
        odoo_image="odoo:16.0",
        postgres_image="postgres:15",
        odoo_versions={
            "17.0": OdooVersionConfig("17.0", "odoo:17.0", "postgres:15"),
            "18.0": OdooVersionConfig("18.0", "odoo:18.0", "postgres:16"),
        },
        repositories={"custom": RepositoryConfig(url="/tmp/repo", target="custom")},
    )


def test_config_loads_odoo_versions_with_postgres_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "config.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "postgres_image": "postgres:15",
                "odoo_versions": {
                    "17.0": {"odoo_image": "odoo:17.0"},
                    "18.0": {"odoo_image": "odoo:18.0", "postgres_image": "postgres:16"},
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("MINI_RUNBOT_CONFIG", str(config))
    settings = Settings.from_environment()
    assert settings.odoo_versions["17.0"].postgres_image == "postgres:15"
    assert settings.odoo_versions["18.0"].postgres_image == "postgres:16"
    assert settings.odoo_image == "odoo:16.0"


def test_config_rejects_invalid_version_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "config.yaml"
    config.write_text(
        yaml.safe_dump({"odoo_versions": {"bad name": {"odoo_image": "odoo:17.0"}}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("MINI_RUNBOT_CONFIG", str(config))
    with pytest.raises(ConfigurationError):
        Settings.from_environment()


def test_resolve_explicit_ref_match_and_default() -> None:
    settings = _settings_with_versions()
    assert settings.resolve_odoo_version("18.0", "feature/x").odoo_image == "odoo:18.0"
    assert settings.resolve_odoo_version(None, "17.0").odoo_image == "odoo:17.0"
    default = settings.resolve_odoo_version(None, "feature/x")
    assert (default.name, default.odoo_image) == ("default", "odoo:16.0")
    with pytest.raises(ConfigurationError):
        settings.resolve_odoo_version("19.0", "19.0")


def test_request_validates_odoo_version() -> None:
    request = CreateBuildRequest(
        repository="custom", ref="17.0", modules=["demo"], odoo_version="17.0"
    )
    assert request.odoo_version == "17.0"
    with pytest.raises(ValueError):
        CreateBuildRequest(repository="custom", ref="17.0", modules=["demo"], odoo_version="../x")


def _build(workspace: Path, **overrides: object) -> Build:
    checkout = workspace / "sources" / "custom"
    checkout.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    values: dict[str, object] = dict(
        id="build-versioned",
        status=BuildStatus.PREPARING,
        requested_ref="17.0",
        repositories=[
            RepositoryRevision(
                name="custom",
                source=str(checkout),
                requested_ref="17.0",
                commit_sha="a" * 40,
                checkout_path=str(checkout),
            )
        ],
        modules=["demo"],
        created_at=now,
        expires_at=now + timedelta(hours=1),
        workspace_path=workspace,
        compose_project_name="build_versioned",
        database_name="build_versioned",
        host_port=18124,
    )
    values.update(overrides)
    return Build(**values)  # type: ignore[arg-type]


def test_render_prefers_build_images_and_falls_back_to_settings(tmp_path: Path) -> None:
    root = tmp_path / "builds"
    settings = Settings(builds_root=root)
    runtime = DockerComposeRuntimeService(settings)

    workspace = root / "build-versioned"
    build = _build(workspace, odoo_image="odoo:18.0", postgres_image="postgres:16")
    runtime.prepare(build.id, workspace)
    runtime.render(build)
    rendered = (workspace / "runtime" / "compose.yaml").read_text(encoding="utf-8")
    assert '"odoo:18.0"' in rendered and '"postgres:16"' in rendered

    legacy_workspace = root / "build-legacy"
    legacy = _build(
        legacy_workspace,
        id="build-legacy",
        compose_project_name="build_legacy",
        database_name="build_legacy",
    )
    runtime.prepare(legacy.id, legacy_workspace)
    runtime.render(legacy)
    rendered = (legacy_workspace / "runtime" / "compose.yaml").read_text(encoding="utf-8")
    assert '"odoo:16.0"' in rendered and '"postgres:15"' in rendered


def test_sqlite_persists_images_and_migrates_old_schema(tmp_path: Path) -> None:
    database = tmp_path / "runbot.db"
    repository = SqliteBuildRepository(f"sqlite:///{database}")
    repository.create_schema()
    build = _build(
        tmp_path / "ws", odoo_version="18.0", odoo_image="odoo:18.0", postgres_image="postgres:16"
    )
    repository.add(build)
    stored = repository.get(build.id)
    assert stored is not None
    assert (stored.odoo_version, stored.odoo_image, stored.postgres_image) == (
        "18.0",
        "odoo:18.0",
        "postgres:16",
    )
    # Re-running schema creation on an existing database must be idempotent.
    SqliteBuildRepository(f"sqlite:///{database}").create_schema()


def test_resolve_infers_profile_from_the_leading_ref_segment() -> None:
    settings = _settings_with_versions()
    assert settings.resolve_odoo_version(None, "17.0-fix-payment").name == "17.0"
    assert settings.resolve_odoo_version(None, "18.0/feature").name == "18.0"
    assert settings.resolve_odoo_version(None, "18.0_mig").name == "18.0"
    assert settings.resolve_odoo_version(None, "17.01").name == "default"
    assert settings.resolve_odoo_version(None, "feature/17.0-x").name == "default"


def test_resolve_prefers_the_longest_matching_profile() -> None:
    settings = Settings(
        odoo_versions={
            "17.0": OdooVersionConfig("17.0", "odoo:17.0", "postgres:15"),
            "17.0-ee": OdooVersionConfig("17.0-ee", "registry.local/odoo-ee:17.0", "postgres:15"),
        }
    )
    assert settings.resolve_odoo_version(None, "17.0-ee-fix").name == "17.0-ee"
    assert settings.resolve_odoo_version(None, "17.0-fix").name == "17.0"


@pytest.mark.parametrize(
    "versions",
    [
        {"default": {"odoo_image": "odoo:17.0"}},
        {"17.0": {"odoo_image": None}},
        {"17.0": {"odoo_image": "  "}},
        {"17.0": {"odoo_image": "odoo:17.0", "postgres_image": None}},
        {"17.0": {"odoo_image": 17}},
    ],
)
def test_config_rejects_reserved_names_and_empty_images(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, versions: dict[str, object]
) -> None:
    config = tmp_path / "config.yaml"
    config.write_text(yaml.safe_dump({"odoo_versions": versions}), encoding="utf-8")
    monkeypatch.setenv("MINI_RUNBOT_CONFIG", str(config))
    with pytest.raises(ConfigurationError):
        Settings.from_environment()
