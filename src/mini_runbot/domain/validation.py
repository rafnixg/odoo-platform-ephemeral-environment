import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SAFE_ALIAS = re.compile(r"^[a-z][a-z0-9_-]{0,62}$")
SAFE_MODULE = re.compile(r"^[a-z][a-z0-9_]{0,127}$")
SAFE_REF = re.compile(r"^(?![-/])(?!.*(?:\.\.|//|@\{|\\))[A-Za-z0-9._/-]{1,200}(?<![/.])$")


class RequestedRepository(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repository: str
    ref: str = Field(min_length=1, max_length=200)

    @field_validator("repository")
    @classmethod
    def validate_repository(cls, value: str) -> str:
        if not SAFE_ALIAS.fullmatch(value):
            raise ValueError("repository must be a safe configured alias")
        return value

    @field_validator("ref")
    @classmethod
    def validate_ref(cls, value: str) -> str:
        if not SAFE_REF.fullmatch(value):
            raise ValueError("ref contains unsafe or unsupported characters")
        return value


class CreateBuildRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repository: str | None = None
    ref: str | None = Field(default=None, min_length=1, max_length=200)
    repositories: list[RequestedRepository] = Field(default_factory=list, max_length=10)
    modules: list[str] = Field(min_length=1, max_length=100)
    ttl_seconds: int = Field(default=14_400, ge=300, le=604_800)

    @field_validator("repository")
    @classmethod
    def validate_repository(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not SAFE_ALIAS.fullmatch(value):
            raise ValueError("repository must be a safe configured alias")
        return value

    @field_validator("ref")
    @classmethod
    def validate_ref(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not SAFE_REF.fullmatch(value):
            raise ValueError("ref contains unsafe or unsupported characters")
        return value

    @field_validator("modules")
    @classmethod
    def validate_modules(cls, values: list[str]) -> list[str]:
        if any(not SAFE_MODULE.fullmatch(value) for value in values):
            raise ValueError("module names must contain lowercase letters, digits, or underscores")
        if len(set(values)) != len(values):
            raise ValueError("module names must be unique")
        return values

    @model_validator(mode="after")
    def validate_repository_selection(self) -> "CreateBuildRequest":
        has_legacy = self.repository is not None or self.ref is not None
        if has_legacy and (self.repository is None or self.ref is None):
            raise ValueError("repository and ref must be provided together")
        if has_legacy and self.repositories:
            raise ValueError("use either repository/ref or repositories, not both")
        selected = self.selected_repositories
        if not selected:
            raise ValueError("at least one repository is required")
        aliases = [item.repository for item in selected]
        if len(set(aliases)) != len(aliases):
            raise ValueError("repository aliases must be unique")
        return self

    @property
    def selected_repositories(self) -> list[RequestedRepository]:
        if self.repositories:
            return self.repositories
        if self.repository is not None and self.ref is not None:
            return [RequestedRepository(repository=self.repository, ref=self.ref)]
        return []
