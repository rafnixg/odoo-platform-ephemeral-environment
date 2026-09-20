from typer.testing import CliRunner

from mini_runbot.cli import main
from mini_runbot.domain.errors import ConfigurationError
from mini_runbot.domain.validation import CreateBuildRequest


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
