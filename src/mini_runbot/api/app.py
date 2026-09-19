from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, status

from mini_runbot.api.schemas import BuildLogsResponse, BuildResponse
from mini_runbot.application.build_manager import BuildManager
from mini_runbot.application.executor import LocalBuildExecutor
from mini_runbot.bootstrap import create_manager
from mini_runbot.config import Settings
from mini_runbot.domain.errors import BuildNotFoundError, MiniRunbotError
from mini_runbot.domain.validation import CreateBuildRequest

app = FastAPI(title="Mini-Runbot", version="0.1.0")


@lru_cache(maxsize=1)
def get_manager() -> BuildManager:
    return create_manager(docker=True)


ManagerDependency = Annotated[BuildManager, Depends(get_manager)]


@lru_cache(maxsize=1)
def get_executor() -> LocalBuildExecutor:
    settings = Settings.from_environment()
    return LocalBuildExecutor(get_manager(), max_workers=settings.max_concurrent_builds)


ExecutorDependency = Annotated[LocalBuildExecutor, Depends(get_executor)]


@app.post("/builds", response_model=BuildResponse, status_code=status.HTTP_202_ACCEPTED)
def create_build(
    request: CreateBuildRequest,
    manager: ManagerDependency,
    executor: ExecutorDependency,
) -> BuildResponse:
    if isinstance(executor, LocalBuildExecutor) and not manager.execution_ready:
        raise HTTPException(
            status_code=503,
            detail="No repositories are configured for build execution",
        )
    try:
        build = manager.create(request)
    except MiniRunbotError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    executor.submit(build.id)
    return BuildResponse.from_domain(build)


@app.get("/builds", response_model=list[BuildResponse])
def list_builds(manager: ManagerDependency) -> list[BuildResponse]:
    return [BuildResponse.from_domain(build) for build in manager.list()]


@app.get("/builds/{build_id}", response_model=BuildResponse)
def get_build(build_id: str, manager: ManagerDependency) -> BuildResponse:
    try:
        return BuildResponse.from_domain(manager.get(build_id))
    except BuildNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/builds/{build_id}", response_model=BuildResponse)
def destroy_build(build_id: str, manager: ManagerDependency) -> BuildResponse:
    try:
        return BuildResponse.from_domain(manager.destroy(build_id))
    except BuildNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/builds/{build_id}/logs", response_model=BuildLogsResponse)
def get_build_logs(
    build_id: str,
    manager: ManagerDependency,
    stage_name: Annotated[str | None, Query(alias="stage")] = None,
) -> BuildLogsResponse:
    limit = 100_000
    try:
        content = manager.read_logs(build_id, stage_name, max_bytes=limit)
    except BuildNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return BuildLogsResponse(
        build_id=build_id,
        stage=stage_name,
        content=content,
        truncated_to_bytes=limit,
    )
