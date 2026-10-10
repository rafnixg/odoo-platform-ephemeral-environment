import os
import re
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


SAFE_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,31}$")
DEFAULT_VERSION_NAME = "default"
REF_SEGMENT_SEPARATORS = ("-", "_", "/")


@dataclass(frozen=True, slots=True)
class OdooVersionConfig:
    name: str
    odoo_image: str
    postgres_image: str


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str = "sqlite:///./mini_runbot.db"
    builds_root: Path = Path("./builds")
    repositories: dict[str, RepositoryConfig] = field(default_factory=dict)
    odoo_image: str = "odoo:16.0"
    postgres_image: str = "postgres:15"
    odoo_versions: dict[str, OdooVersionConfig] = field(default_factory=dict)
    port_start: int = 18_000
    port_end: int = 19_999
    command_timeout_seconds: int = 900
    health_timeout_seconds: int = 120
    max_concurrent_builds: int = 2
    cleanup_interval_seconds: int = 0
    destroyed_retention_seconds: int = 0
    load_demo_data: bool = True
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

        default_odoo_image = os.getenv(
            "MINI_RUNBOT_ODOO_IMAGE", str(raw.get("odoo_image", "odoo:16.0"))
        )
        default_postgres_image = str(raw.get("postgres_image", "postgres:15"))
        raw_versions = raw.get("odoo_versions", {}) or {}
        if not isinstance(raw_versions, dict):
            raise ConfigurationError("odoo_versions must be a mapping")
        odoo_versions: dict[str, OdooVersionConfig] = {}
        for name, item in raw_versions.items():
            name = str(name)
            if not SAFE_VERSION.fullmatch(name):
                raise ConfigurationError(f"Invalid odoo_versions entry name: {name}")
            if name == DEFAULT_VERSION_NAME:
                raise ConfigurationError(
                    f"odoo_versions entry name is reserved: {DEFAULT_VERSION_NAME}"
                )
            if not isinstance(item, dict) or "odoo_image" not in item:
                raise ConfigurationError(f"Odoo version {name} must define odoo_image")
            images = {
                "odoo_image": item["odoo_image"],
                "postgres_image": item.get("postgres_image", default_postgres_image),
            }
            for key, image in images.items():
                if not isinstance(image, str) or not image.strip():
                    raise ConfigurationError(f"Odoo version {name} has an empty {key}")
            odoo_versions[name] = OdooVersionConfig(
                name=name,
                odoo_image=images["odoo_image"].strip(),
                postgres_image=images["postgres_image"].strip(),
            )

        cleanup_interval_seconds = int(
            os.getenv(
                "MINI_RUNBOT_CLEANUP_INTERVAL_SECONDS",
                str(raw.get("cleanup_interval_seconds", 0)),
            )
        )
        if cleanup_interval_seconds < 0:
            raise ConfigurationError("cleanup_interval_seconds must be zero or positive")
        destroyed_retention_seconds = int(raw.get("destroyed_retention_seconds", 0))
        if destroyed_retention_seconds < 0:
            raise ConfigurationError("destroyed_retention_seconds must be zero or positive")

        return cls(
            database_url=os.getenv(
                "MINI_RUNBOT_DATABASE_URL",
                str(raw.get("database_url", "sqlite:///./mini_runbot.db")),
            ),
            builds_root=Path(
                os.getenv("MINI_RUNBOT_BUILDS_ROOT", str(raw.get("builds_root", "./builds")))
            ),
            repositories=repositories,
            odoo_image=default_odoo_image,
            postgres_image=default_postgres_image,
            odoo_versions=odoo_versions,
            port_start=int(raw.get("port_start", 18_000)),
            port_end=int(raw.get("port_end", 19_999)),
            command_timeout_seconds=int(raw.get("command_timeout_seconds", 900)),
            health_timeout_seconds=int(raw.get("health_timeout_seconds", 120)),
            max_concurrent_builds=int(raw.get("max_concurrent_builds", 2)),
            cleanup_interval_seconds=cleanup_interval_seconds,
            destroyed_retention_seconds=destroyed_retention_seconds,
            load_demo_data=bool(raw.get("load_demo_data", True)),
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

    def resolve_odoo_version(
        self, requested_version: str | None, requested_ref: str
    ) -> OdooVersionConfig:
        """Pick the image pair for a build.

        Explicit request wins; otherwise a profile whose name matches the Git ref
        is used, exactly or as its leading segment (17.0-fix-payment -> 17.0);
        otherwise the global odoo_image/postgres_image act as default.
        """
        if requested_version is not None:
            try:
                return self.odoo_versions[requested_version]
            except KeyError as exc:
                raise ConfigurationError(
                    f"Odoo version is not configured: {requested_version}"
                ) from exc
        inferred = self.odoo_versions.get(requested_ref)
        if inferred is not None:
            return inferred
        prefixed = [
            name
            for name in self.odoo_versions
            if requested_ref.startswith(name)
            and requested_ref[len(name) : len(name) + 1] in REF_SEGMENT_SEPARATORS
        ]
        if prefixed:
            return self.odoo_versions[max(prefixed, key=len)]
        return OdooVersionConfig(
            name=DEFAULT_VERSION_NAME,
            odoo_image=self.odoo_image,
            postgres_image=self.postgres_image,
        )
