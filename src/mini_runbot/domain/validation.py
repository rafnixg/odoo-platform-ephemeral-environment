import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

SAFE_ALIAS = re.compile(r"^[a-z][a-z0-9_-]{0,62}$")
SAFE_MODULE = re.compile(r"^[a-z][a-z0-9_]{0,127}$")
SAFE_REF = re.compile(r"^(?![-/])(?!.*(?:\.\.|//|@\{|\\))[A-Za-z0-9._/-]{1,200}(?<![/.])$")


class CreateBuildRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repository: str
    ref: str = Field(min_length=1, max_length=200)
    modules: list[str] = Field(min_length=1, max_length=100)
    ttl_seconds: int = Field(default=14_400, ge=300, le=604_800)

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

    @field_validator("modules")
    @classmethod
    def validate_modules(cls, values: list[str]) -> list[str]:
        if any(not SAFE_MODULE.fullmatch(value) for value in values):
            raise ValueError("module names must contain lowercase letters, digits, or underscores")
        if len(set(values)) != len(values):
            raise ValueError("module names must be unique")
        return values
