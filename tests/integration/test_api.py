from pathlib import Path

from fastapi.testclient import TestClient

from mini_runbot.adapters.persistence.sqlite import SqliteBuildRepository
from mini_runbot.adapters.runtime.local import LocalRuntimeService
from mini_runbot.api.app import app, get_manager
from mini_runbot.application.build_manager import BuildManager


def test_api_create_get_list_and_destroy(tmp_path: Path) -> None:
    repository = SqliteBuildRepository(f"sqlite:///{tmp_path / 'api.db'}")
    repository.create_schema()
    builds_root = tmp_path / "builds"
    manager = BuildManager(repository, LocalRuntimeService(builds_root), builds_root)
    app.dependency_overrides[get_manager] = lambda: manager

    try:
        with TestClient(app) as client:
            response = client.post(
                "/builds",
                json={
                    "repository": "custom",
                    "ref": "feature/api",
                    "modules": ["demo_module"],
                },
            )
            assert response.status_code == 201
            build_id = response.json()["id"]
            assert response.json()["status"] == "new"

            assert client.get(f"/builds/{build_id}").json()["id"] == build_id
            assert [item["id"] for item in client.get("/builds").json()] == [build_id]

            destroyed = client.delete(f"/builds/{build_id}")
            assert destroyed.status_code == 200
            assert destroyed.json()["status"] == "destroyed"
            assert client.delete(f"/builds/{build_id}").json()["status"] == "destroyed"
    finally:
        app.dependency_overrides.clear()

