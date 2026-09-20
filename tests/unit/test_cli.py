from typer.testing import CliRunner

from mini_runbot.cli import main
from mini_runbot.domain.errors import ConfigurationError


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
