from datetime import UTC, datetime
from pathlib import Path

from mini_runbot.adapters.persistence.sqlite import SqliteBuildRepository
from mini_runbot.adapters.runtime.local import LocalRuntimeService
from mini_runbot.application.build_manager import BuildManager
from mini_runbot.domain.enums import BuildStatus, StageStatus
from mini_runbot.domain.models import StageResult
from mini_runbot.domain.validation import CreateBuildRequest


def test_sqlite_create_read_list_destroy_and_preserve_logs(tmp_path: Path) -> None:
    builds_root = tmp_path / "builds"
    repository = SqliteBuildRepository(f"sqlite:///{tmp_path / 'test.db'}")
    repository.create_schema()
    manager = BuildManager(repository, LocalRuntimeService(builds_root), builds_root)

    created = manager.create(
        CreateBuildRequest(repository="custom", ref="feature/demo", modules=["demo_module"])
    )
    log_file = created.workspace_path / "logs" / "audit.log"
    log_file.write_text("retained evidence", encoding="utf-8")

    assert manager.get(created.id).status == BuildStatus.NEW
    assert [item.id for item in manager.list()] == [created.id]
    assert (created.workspace_path / "runtime").is_dir()

    created.stages.append(
        StageResult(
            name="audit",
            status=StageStatus.SUCCESS,
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
            duration_seconds=0.01,
            exit_code=0,
            log_path=str(log_file),
            summary="persisted",
        )
    )
    repository.update(created)
    assert manager.get(created.id).stages[0].summary == "persisted"
    assert "retained evidence" in manager.read_logs(created.id, "audit")

    destroyed = manager.destroy(created.id)
    repeated = manager.destroy(created.id)

    assert destroyed.status == BuildStatus.DESTROYED
    assert repeated.status == BuildStatus.DESTROYED
    assert not (created.workspace_path / "runtime").exists()
    assert log_file.read_text(encoding="utf-8") == "retained evidence"
