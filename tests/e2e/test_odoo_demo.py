import os
from pathlib import Path

import pytest

from mini_runbot.bootstrap import create_manager
from mini_runbot.config import RepositoryConfig, Settings
from mini_runbot.domain.enums import BuildStatus
from mini_runbot.domain.validation import CreateBuildRequest

pytestmark = pytest.mark.docker


@pytest.mark.skipif(
    os.getenv("MINI_RUNBOT_RUN_DOCKER_TESTS") != "1",
    reason="set MINI_RUNBOT_RUN_DOCKER_TESTS=1 to run the real Odoo fixture",
)
def test_real_odoo_install_test_healthcheck_and_destroy(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[2]
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'e2e.db'}",
        builds_root=tmp_path / "builds",
        repositories={
            "demo": RepositoryConfig(
                url=str(project_root),
                target="demo-source",
                addons_subpath="demo_addons",
            )
        },
        port_start=18200,
        port_end=18299,
        health_timeout_seconds=180,
    )
    manager = create_manager(settings, docker=True)
    build = manager.create(
        CreateBuildRequest(repository="demo", ref="HEAD", modules=["mini_runbot_demo"])
    )

    try:
        result = manager.execute(build.id)
        assert result.status == BuildStatus.RUNNING
        assert result.repositories[0].commit_sha
        assert result.preview_url
    finally:
        manager.destroy(build.id)

    assert manager.get(build.id).status == BuildStatus.DESTROYED
