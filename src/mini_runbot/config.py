import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from mini_runbot.domain.errors import ConfigurationError
from mini_runbot.domain.validation import SAFE_ALIAS


@dataclass(frozen=True, slots=True)
class RepositoryConfig:
    url: str
    target: str
    addons_subpath: str = "."
    default_ref: str = "16.0"
    allow_request_ref: bool = True
    addons_priority: int = 100


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str = "sqlite:///./mini_runbot.db"
    builds_root: Path = Path("./builds")
    repositories: dict[str, RepositoryConfig] = field(default_factory=dict)
    odoo_image: str = "odoo:16.0"
    postgres_image: str = "postgres:15"
    port_start: int = 18_000
    port_end: int = 19_999
    command_timeout_seconds: int = 900
    health_timeout_seconds: int = 120
    max_concurrent_builds: int = 2
    cleanup_interval_seconds: int = 0
    retain_failed_runtime: bool = False

    @classmethod
    def from_environment(cls) -> "Settings":
        config_path = os.getenv("MINI_RUNBOT_CONFIG")
        raw: dict[str, Any] = {}
        if config_path:
            path = Path(config_path).resolve()
            if not path.is_file():
                raise ConfigurationError(f"Configuration file does not exist: {path}")
            loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if not isinstance(loaded, dict):
                raise ConfigurationError("Configuration root must be a mapping")
            raw = loaded

        raw_repositories = raw.get("repositories", {})
        if not isinstance(raw_repositories, dict):
            raise ConfigurationError("repositories must be a mapping")
        repositories: dict[str, RepositoryConfig] = {}
        for alias, item in raw_repositories.items():
            if not isinstance(alias, str) or not SAFE_ALIAS.fullmatch(alias):
                raise ConfigurationError(f"Invalid repository alias: {alias}")
            if not isinstance(item, dict) or "url" not in item:
                raise ConfigurationError(f"Repository {alias} must define url")
            target = str(item.get("target", alias))
            if not SAFE_ALIAS.fullmatch(target):
                raise ConfigurationError(f"Invalid target for repository {alias}")
            repositories[alias] = RepositoryConfig(
                url=str(item["url"]),
                target=target,
                addons_subpath=str(item.get("addons_subpath", ".")),
                default_ref=str(item.get("default_ref", "16.0")),
                allow_request_ref=bool(item.get("allow_request_ref", True)),
                addons_priority=int(item.get("addons_priority", 100)),
            )
            subpath = Path(repositories[alias].addons_subpath)
            if subpath.is_absolute() or ".." in subpath.parts:
                raise ConfigurationError(f"Invalid addons_subpath for repository {alias}")

        targets: dict[str, str] = {}
        for alias, repository in repositories.items():
            previous = targets.get(repository.target)
            if previous is not None:
                raise ConfigurationError(
                    f"Repositories {previous} and {alias} use the same target: "
                    f"{repository.target}"
                )
            targets[repository.target] = alias

        cleanup_interval_seconds = int(
            os.getenv(
                "MINI_RUNBOT_CLEANUP_INTERVAL_SECONDS",
                str(raw.get("cleanup_interval_seconds", 0)),
            )
        )
        if cleanup_interval_seconds < 0:
            raise ConfigurationError("cleanup_interval_seconds must be zero or positive")

        return cls(
            database_url=os.getenv(
                "MINI_RUNBOT_DATABASE_URL",
                str(raw.get("database_url", "sqlite:///./mini_runbot.db")),
            ),
            builds_root=Path(
                os.getenv("MINI_RUNBOT_BUILDS_ROOT", str(raw.get("builds_root", "./builds")))
            ),
            repositories=repositories,
            odoo_image=os.getenv(
                "MINI_RUNBOT_ODOO_IMAGE", str(raw.get("odoo_image", "odoo:16.0"))
            ),
            postgres_image=str(raw.get("postgres_image", "postgres:15")),
            port_start=int(raw.get("port_start", 18_000)),
            port_end=int(raw.get("port_end", 19_999)),
            command_timeout_seconds=int(raw.get("command_timeout_seconds", 900)),
            health_timeout_seconds=int(raw.get("health_timeout_seconds", 120)),
            max_concurrent_builds=int(raw.get("max_concurrent_builds", 2)),
            cleanup_interval_seconds=cleanup_interval_seconds,
            retain_failed_runtime=bool(raw.get("retain_failed_runtime", False)),
        )

    def repository(self, alias: str, requested_ref: str) -> RepositoryConfig:
        try:
            repository = self.repositories[alias]
        except KeyError as exc:
            raise ConfigurationError(f"Repository alias is not allowed: {alias}") from exc
        if not repository.allow_request_ref and requested_ref != repository.default_ref:
            raise ConfigurationError(f"Repository {alias} does not allow request refs")
        return repository
