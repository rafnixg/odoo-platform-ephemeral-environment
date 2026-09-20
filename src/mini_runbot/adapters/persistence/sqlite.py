from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sqlalchemy import (
    JSON,
    DateTime,
    Integer,
    String,
    create_engine,
    delete,
    inspect,
    select,
    text,
    update,
)
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from mini_runbot.domain.enums import BuildStatus, StageStatus
from mini_runbot.domain.errors import ConcurrentUpdateError
from mini_runbot.domain.models import Build, RepositoryRevision, StageResult


class Base(DeclarativeBase):
    pass


class BuildRow(Base):
    __tablename__ = "builds"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    repositories: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    modules: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    host_port: Mapped[int | None] = mapped_column(Integer)
    database_name: Mapped[str] = mapped_column(String(64), nullable=False)
    compose_project_name: Mapped[str] = mapped_column(String(64), nullable=False)
    workspace_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    preview_url: Mapped[str | None] = mapped_column(String(2048))
    failure_stage: Mapped[str | None] = mapped_column(String(64))
    failure_message: Mapped[str | None] = mapped_column(String(1000))
    stages: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class PortLeaseRow(Base):
    __tablename__ = "port_leases"

    port: Mapped[int] = mapped_column(Integer, primary_key=True)
    build_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)


class SqliteBuildRepository:
    def __init__(self, database_url: str) -> None:
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self.engine = create_engine(database_url, connect_args=connect_args)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)
        columns = {item["name"] for item in inspect(self.engine).get_columns("builds")}
        if "stages" not in columns:
            with self.engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE builds ADD COLUMN stages JSON NOT NULL DEFAULT '[]'")
                )
        self._seed_port_leases()

    def add(self, build: Build) -> None:
        with self.sessions.begin() as session:
            session.add(self._to_row(build))

    def get(self, build_id: str) -> Build | None:
        with self.sessions() as session:
            row = session.get(BuildRow, build_id)
            return self._to_domain(row) if row else None

    def list(self) -> list[Build]:
        with self.sessions() as session:
            rows = session.scalars(select(BuildRow).order_by(BuildRow.created_at.desc())).all()
            return [self._to_domain(row) for row in rows]

    def update(self, build: Build) -> None:
        previous_version = build.version
        values = self._values(build)
        values["version"] = previous_version + 1
        with self.sessions.begin() as session:
            result = session.execute(
                update(BuildRow)
                .where(BuildRow.id == build.id, BuildRow.version == previous_version)
                .values(**values)
            )
            if result.rowcount != 1:
                raise ConcurrentUpdateError(f"Build {build.id} changed concurrently")
        build.version += 1

    def delete(self, build_id: str) -> None:
        with self.sessions.begin() as session:
            session.execute(
                delete(PortLeaseRow).where(PortLeaseRow.build_id == build_id)
            )
            session.execute(delete(BuildRow).where(BuildRow.id == build_id))

    def try_acquire_port(self, build_id: str, port: int) -> bool:
        try:
            with self.sessions.begin() as session:
                existing = session.scalar(
                    select(PortLeaseRow).where(PortLeaseRow.build_id == build_id)
                )
                if existing is not None:
                    return existing.port == port
                session.add(PortLeaseRow(port=port, build_id=build_id))
                session.flush()
        except IntegrityError:
            return False
        return True

    def release_port(self, build_id: str, port: int) -> None:
        with self.sessions.begin() as session:
            session.execute(
                delete(PortLeaseRow).where(
                    PortLeaseRow.port == port, PortLeaseRow.build_id == build_id
                )
            )

    def reconcile_port_leases(self) -> list[int]:
        terminal = {BuildStatus.DESTROYED.value}
        released: list[int] = []
        with self.sessions.begin() as session:
            builds = {row.id: row for row in session.scalars(select(BuildRow)).all()}
            leases = session.scalars(select(PortLeaseRow)).all()
            for lease in leases:
                build = builds.get(lease.build_id)
                if (
                    build is None
                    or build.status in terminal
                    or build.host_port != lease.port
                ):
                    released.append(lease.port)
                    session.delete(lease)
            self._insert_missing_port_leases(session, builds.values(), terminal)
        return released

    def _seed_port_leases(self) -> None:
        terminal = {BuildStatus.DESTROYED.value}
        with self.sessions.begin() as session:
            self._insert_missing_port_leases(
                session, session.scalars(select(BuildRow)).all(), terminal
            )

    @staticmethod
    def _insert_missing_port_leases(session, builds, terminal: set[str]) -> None:
        for build in builds:
            if build.host_port is None or build.status in terminal:
                continue
            statement = (
                sqlite_insert(PortLeaseRow)
                .values(port=build.host_port, build_id=build.id)
                .on_conflict_do_nothing()
            )
            session.execute(statement)

    @staticmethod
    def _repo_dict(repo: RepositoryRevision) -> dict[str, object]:
        return {
            "name": repo.name,
            "source": repo.source,
            "requested_ref": repo.requested_ref,
            "commit_sha": repo.commit_sha,
            "checkout_path": repo.checkout_path,
            "addons_priority": repo.addons_priority,
        }

    def _values(self, build: Build) -> dict[str, object]:
        return {
            "status": build.status.value,
            "requested_ref": build.requested_ref,
            "repositories": [self._repo_dict(repo) for repo in build.repositories],
            "modules": build.modules,
            "created_at": build.created_at,
            "started_at": build.started_at,
            "finished_at": build.finished_at,
            "expires_at": build.expires_at,
            "host_port": build.host_port,
            "database_name": build.database_name,
            "compose_project_name": build.compose_project_name,
            "workspace_path": str(build.workspace_path),
            "preview_url": build.preview_url,
            "failure_stage": build.failure_stage,
            "failure_message": build.failure_message,
            "stages": [self._stage_dict(stage) for stage in build.stages],
        }

    @staticmethod
    def _stage_dict(stage: StageResult) -> dict[str, object]:
        return {
            "name": stage.name,
            "status": stage.status.value,
            "started_at": stage.started_at.isoformat() if stage.started_at else None,
            "finished_at": stage.finished_at.isoformat() if stage.finished_at else None,
            "duration_seconds": stage.duration_seconds,
            "exit_code": stage.exit_code,
            "log_path": stage.log_path,
            "summary": stage.summary,
            "metadata": stage.metadata,
        }

    def _to_row(self, build: Build) -> BuildRow:
        return BuildRow(id=build.id, version=build.version, **self._values(build))

    @staticmethod
    def _to_domain(row: BuildRow) -> Build:
        return Build(
            id=row.id,
            status=BuildStatus(row.status),
            requested_ref=row.requested_ref,
            repositories=[RepositoryRevision(**item) for item in row.repositories],
            modules=list(row.modules),
            created_at=row.created_at,
            started_at=row.started_at,
            finished_at=row.finished_at,
            expires_at=row.expires_at,
            host_port=row.host_port,
            database_name=row.database_name,
            compose_project_name=row.compose_project_name,
            workspace_path=Path(row.workspace_path),
            preview_url=row.preview_url,
            failure_stage=row.failure_stage,
            failure_message=row.failure_message,
            stages=[
                StageResult(
                    name=item["name"],
                    status=StageStatus(item["status"]),
                    started_at=(
                        datetime.fromisoformat(item["started_at"])
                        if item.get("started_at")
                        else None
                    ),
                    finished_at=(
                        datetime.fromisoformat(item["finished_at"])
                        if item.get("finished_at")
                        else None
                    ),
                    duration_seconds=item.get("duration_seconds"),
                    exit_code=item.get("exit_code"),
                    log_path=item.get("log_path"),
                    summary=item.get("summary"),
                    metadata=item.get("metadata", {}),
                )
                for item in row.stages
            ],
            version=row.version,
        )
