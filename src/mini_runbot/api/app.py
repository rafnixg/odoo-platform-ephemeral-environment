from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status

from mini_runbot.api.schemas import BuildResponse
from mini_runbot.application.build_manager import BuildManager
from mini_runbot.bootstrap import create_manager
from mini_runbot.domain.errors import BuildNotFoundError
from mini_runbot.domain.validation import CreateBuildRequest

app = FastAPI(title="Mini-Runbot", version="0.1.0")


@lru_cache(maxsize=1)
def get_manager() -> BuildManager:
    return create_manager()


ManagerDependency = Annotated[BuildManager, Depends(get_manager)]


@app.post("/builds", response_model=BuildResponse, status_code=status.HTTP_201_CREATED)
def create_build(
    request: CreateBuildRequest,
    manager: ManagerDependency,
) -> BuildResponse:
    return BuildResponse.from_domain(manager.create(request))


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
