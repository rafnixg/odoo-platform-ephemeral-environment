from pathlib import Path

import yaml
from typer.testing import CliRunner

from mini_runbot.cli import main
from mini_runbot.domain.errors import ConfigurationError
from mini_runbot.domain.validation import CreateBuildRequest


def test_init_with_defaults_creates_loadable_config(tmp_path: Path) -> None:
    output = tmp_path / "config.local.yaml"

    result = CliRunner().invoke(
        main.app,
        ["init", "--defaults", "--output", str(output)],
    )

    assert result.exit_code == 0, result.output
    loaded = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert loaded["database_url"] == "sqlite:///./mini_runbot.db"
    assert loaded["repositories"]["custom"]["default_ref"] == "16.0"
    assert "PowerShell" in result.output
    assert "Bash" in result.output
    assert "mini-runbot doctor" in result.output


def test_init_interactive_accepts_example_defaults(tmp_path: Path) -> None:
    output = tmp_path / "config.local.yaml"

    result = CliRunner().invoke(
        main.app,
        ["init", "--output", str(output)],
        input="\n" * 30,
    )

    assert result.exit_code == 0, result.output
    loaded = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert loaded["port_start"] == 18_000
    assert loaded["port_end"] == 19_999
    assert loaded["load_demo_data"] is True
    assert loaded["retain_failed_runtime"] is False
    assert list(loaded["repositories"]) == ["custom"]


def test_init_refuses_to_overwrite_existing_config(tmp_path: Path) -> None:
    output = tmp_path / "config.local.yaml"
    output.write_text("owned: true\n", encoding="utf-8")

    result = CliRunner().invoke(
        main.app,
        ["init", "--defaults", "--output", str(output)],
    )

    assert result.exit_code == 1
    assert "already exists" in result.output
    assert output.read_text(encoding="utf-8") == "owned: true\n"


def test_destroy_uses_docker_runtime(monkeypatch) -> None:
    docker_arguments: list[bool] = []

    def fake_create_manager(*, docker: bool = False):
        docker_arguments.append(docker)
        raise ConfigurationError("controlled stop")

    monkeypatch.setattr(main, "create_manager", fake_create_manager)

    result = CliRunner().invoke(main.app, ["build", "destroy", "build-test"])

    assert result.exit_code == 1
    assert docker_arguments == [True]
    assert "controlled stop" in result.output


def test_create_parses_repeated_extra_repositories(monkeypatch) -> None:
    requests: list[CreateBuildRequest] = []

    class FakeBuild:
        id = "build-test"

    class FakeManager:
        def create(self, request: CreateBuildRequest):
            requests.append(request)
            return FakeBuild()

        def execute(self, build_id: str):
            return FakeBuild()

    monkeypatch.setattr(main, "create_manager", lambda *, docker=False: FakeManager())
    monkeypatch.setattr(main, "print_build", lambda *args, **kwargs: None)

    result = CliRunner().invoke(
        main.app,
        [
            "build",
            "create",
            "--repo",
            "custom",
            "--ref",
            "feature/main",
            "--extra-repo",
            "oca=16.0",
            "--extra-repo",
            "enterprise=16.0",
            "--modules",
            "custom_sale",
            "--run",
        ],
    )

    assert result.exit_code == 0, result.output
    assert [
        (item.repository, item.ref) for item in requests[0].selected_repositories
    ] == [
        ("custom", "feature/main"),
        ("oca", "16.0"),
        ("enterprise", "16.0"),
    ]


def test_create_reports_duplicate_repository_without_traceback() -> None:
    result = CliRunner().invoke(
        main.app,
        [
            "build",
            "create",
            "--repo",
            "custom",
            "--ref",
            "16.0",
            "--extra-repo",
            "custom=feature/other",
            "--modules",
            "custom_sale",
        ],
    )

    assert result.exit_code == 2
    assert "repository aliases must be unique" in result.output
    assert "Traceback" not in result.output
