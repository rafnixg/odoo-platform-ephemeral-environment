from pathlib import Path

from fastapi.testclient import TestClient

from mini_runbot.adapters.persistence.sqlite import SqliteBuildRepository
from mini_runbot.adapters.runtime.local import LocalRuntimeService
from mini_runbot.api.app import app, get_executor, get_manager
from mini_runbot.application.build_manager import BuildManager


def test_api_create_get_list_and_destroy(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("MINI_RUNBOT_CONFIG", raising=False)
    repository = SqliteBuildRepository(f"sqlite:///{tmp_path / 'api.db'}")
    repository.create_schema()
    builds_root = tmp_path / "builds"
    manager = BuildManager(repository, LocalRuntimeService(builds_root), builds_root)
    app.dependency_overrides[get_manager] = lambda: manager
    submitted: list[str] = []

    class RecordingExecutor:
        def submit(self, build_id: str) -> None:
            submitted.append(build_id)

        def is_active(self, build_id: str) -> bool:
            return False

    app.dependency_overrides[get_executor] = RecordingExecutor

    try:
        with TestClient(app) as client:
            dashboard = client.get("/")
            assert dashboard.status_code == 200
            assert "Mini-Runbot" in dashboard.text
            assert client.get("/assets/styles.css").status_code == 200
            assert client.get("/assets/app.js").status_code == 200
            public_config = client.get("/app-config")
            assert public_config.status_code == 200
            assert "repositories" in public_config.json()

            response = client.post(
                "/builds",
                json={
                    "repository": "custom",
                    "ref": "feature/api",
                    "modules": ["demo_module"],
                },
            )
            assert response.status_code == 202
            build_id = response.json()["id"]
            assert response.json()["status"] == "new"
            assert response.json()["created_at"].endswith("Z")
            assert response.json()["expires_at"].endswith("Z")
            assert submitted == [build_id]

            assert client.get(f"/builds/{build_id}").json()["id"] == build_id
            assert [item["id"] for item in client.get("/builds").json()] == [build_id]

            destroyed = client.delete(f"/builds/{build_id}")
            assert destroyed.status_code == 200
            assert destroyed.json()["status"] == "destroyed"
            assert client.delete(f"/builds/{build_id}").json()["status"] == "destroyed"

            logs = client.get(f"/builds/{build_id}/logs")
            assert logs.status_code == 200
            assert logs.json()["content"] == ""
    finally:
        app.dependency_overrides.clear()


def test_api_rejects_destroy_while_build_execution_is_active(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.delenv("MINI_RUNBOT_CONFIG", raising=False)
    repository = SqliteBuildRepository(f"sqlite:///{tmp_path / 'active-api.db'}")
    repository.create_schema()
    builds_root = tmp_path / "builds"
    manager = BuildManager(repository, LocalRuntimeService(builds_root), builds_root)

    class ActiveExecutor:
        def submit(self, build_id: str) -> None:
            pass

        def is_active(self, build_id: str) -> bool:
            return True

    app.dependency_overrides[get_manager] = lambda: manager
    app.dependency_overrides[get_executor] = ActiveExecutor

    try:
        with TestClient(app) as client:
            created = client.post(
                "/builds",
                json={
                    "repository": "custom",
                    "ref": "feature/active",
                    "modules": ["demo_module"],
                },
            )
            build_id = created.json()["id"]

            response = client.delete(f"/builds/{build_id}")

            assert response.status_code == 409
            assert "still active" in response.json()["detail"]
            assert manager.get(build_id).status.value == "new"
    finally:
        app.dependency_overrides.clear()


def test_public_config_does_not_expose_repository_paths(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "private-source"
    source.mkdir()
    config = tmp_path / "config.yaml"
    config.write_text(
        "repositories:\n  custom:\n    url: "
        + source.as_posix()
        + "\n    default_ref: '16.0'\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("MINI_RUNBOT_CONFIG", str(config))

    with TestClient(app) as client:
        response = client.get("/app-config")

    assert response.status_code == 200
    assert response.json()["repositories"] == [
        {
            "alias": "custom",
            "default_ref": "16.0",
            "allow_request_ref": True,
            "addons_priority": 100,
        }
    ]
    assert str(source) not in response.text


def test_api_accepts_multiple_repositories(tmp_path: Path) -> None:
    repository = SqliteBuildRepository(f"sqlite:///{tmp_path / 'multi-api.db'}")
    repository.create_schema()
    builds_root = tmp_path / "builds"
    manager = BuildManager(repository, LocalRuntimeService(builds_root), builds_root)
    app.dependency_overrides[get_manager] = lambda: manager

    class RecordingExecutor:
        def submit(self, build_id: str) -> None:
            pass

        def is_active(self, build_id: str) -> bool:
            return False

    app.dependency_overrides[get_executor] = RecordingExecutor
    try:
        with TestClient(app) as client:
            response = client.post(
                "/builds",
                json={
                    "repositories": [
                        {"repository": "oca", "ref": "16.0"},
                        {"repository": "custom", "ref": "feature/api"},
                    ],
                    "modules": ["demo_module"],
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert [item["name"] for item in response.json()["repositories"]] == [
        "oca",
        "custom",
    ]
    assert [item["requested_ref"] for item in response.json()["repositories"]] == [
        "16.0",
        "feature/api",
    ]
