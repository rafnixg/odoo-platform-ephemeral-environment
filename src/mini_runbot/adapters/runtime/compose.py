from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from mini_runbot.config import Settings
from mini_runbot.domain.errors import RuntimeOperationError
from mini_runbot.domain.models import Build
from mini_runbot.ports.services import CommandResult, RuntimeInspection


class DockerComposeRuntimeService:
    def __init__(self, settings: Settings, template_root: Path | None = None) -> None:
        self.settings = settings
        root = template_root or Path(__file__).resolve().parents[4] / "templates"
        self.environment = Environment(
            loader=FileSystemLoader(root),
            undefined=StrictUndefined,
            autoescape=select_autoescape(default=False),
            keep_trailing_newline=True,
        )

    def prepare(self, build_id: str, workspace_path: Path) -> None:
        self._validated_workspace(build_id, workspace_path)
        (workspace_path / "logs").mkdir(parents=True, exist_ok=True)
        (workspace_path / "runtime").mkdir(parents=True, exist_ok=True)

    def render(self, build: Build) -> CommandResult:
        started = time.monotonic()
        if build.host_port is None:
            raise RuntimeOperationError("Build has no allocated host port")
        if any(not repository.checkout_path for repository in build.repositories):
            raise RuntimeOperationError("All repositories must be checked out before rendering")
        repositories = sorted(
            build.repositories, key=lambda item: (item.addons_priority, item.name)
        )
        addons_path = ",".join(
            ["/usr/lib/python3/dist-packages/odoo/addons"]
            + [f"/mnt/addons/{item.name}" for item in repositories]
        )
        rendered = self.environment.get_template("compose.yaml.j2").render(
            compose_project_name=build.compose_project_name,
            database_name=build.database_name,
            host_port=build.host_port,
            odoo_image=self.settings.odoo_image,
            postgres_image=self.settings.postgres_image,
            repositories=repositories,
            addons_path=addons_path,
        )
        path = self._compose_path(build)
        path.write_text(rendered, encoding="utf-8")
        log_path = build.workspace_path / "logs" / "render.log"
        log_path.write_text(f"Rendered {path.name}\n", encoding="utf-8")
        return self._result(started, log_path, "Compose configuration rendered")

    def validate(self, build: Build) -> CommandResult:
        return self._run(build, "compose_validate", ["config", "--quiet"])

    def start_database(self, build: Build) -> CommandResult:
        return self._run(build, "database", ["up", "-d", "--wait", "db"])

    def install_modules(self, build: Build) -> CommandResult:
        return self._run(
            build,
            "install",
            [
                "run",
                "--rm",
                "odoo",
                "odoo",
                "-d",
                build.database_name,
                "-i",
                ",".join(build.modules),
                "--without-demo=all",
                "--stop-after-init",
                f"--addons-path={self._addons_path(build)}",
            ],
        )

    def test_modules(self, build: Build) -> CommandResult:
        tags = ",".join(f"/{module}" for module in build.modules)
        return self._run(
            build,
            "test",
            [
                "run",
                "--rm",
                "odoo",
                "odoo",
                "-d",
                build.database_name,
                "--test-enable",
                f"--test-tags={tags}",
                "--stop-after-init",
                f"--addons-path={self._addons_path(build)}",
            ],
        )

    def start_server(self, build: Build) -> CommandResult:
        return self._run(build, "start", ["up", "-d", "odoo"])

    def wait_healthy(self, build: Build) -> CommandResult:
        if not build.preview_url:
            raise RuntimeOperationError("Build has no preview URL")
        started = time.monotonic()
        deadline = started + self.settings.health_timeout_seconds
        last_error = "no response"
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(build.preview_url, timeout=5) as response:
                    if response.status < 500:
                        log_path = build.workspace_path / "logs" / "healthcheck.log"
                        log_path.write_text(
                            f"HTTP {response.status} from {build.preview_url}\n", encoding="utf-8"
                        )
                        return self._result(started, log_path, "Odoo HTTP healthcheck passed")
            except (OSError, urllib.error.URLError) as exc:
                last_error = str(exc)
            time.sleep(1)
        raise RuntimeOperationError(f"Odoo healthcheck timed out: {last_error}")

    def inspect(self, build: Build) -> RuntimeInspection:
        compose_path = self._compose_path(build)
        if not compose_path.is_file():
            return RuntimeInspection(False, False, (), "Compose configuration is absent")
        command = [
            "docker",
            "compose",
            "--project-name",
            build.compose_project_name,
            "--file",
            str(compose_path),
            "ps",
            "--all",
            "--format",
            "json",
        ]
        try:
            result = subprocess.run(
                command,
                cwd=build.workspace_path,
                capture_output=True,
                text=True,
                timeout=self.settings.command_timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeOperationError(
                f"Docker runtime inspection could not complete: {exc}"
            ) from exc
        log_path = build.workspace_path / "logs" / "runtime_inspect.log"
        log_path.write_text(f"{result.stdout}{result.stderr}"[-1_000_000:], encoding="utf-8")
        if result.returncode != 0:
            raise RuntimeOperationError(f"Docker runtime inspection failed; see {log_path}")
        entries = self._parse_compose_ps(result.stdout)
        services = tuple(
            sorted(
                str(item.get("Service"))
                for item in entries
                if item.get("Service")
            )
        )
        running_services = {
            str(item.get("Service"))
            for item in entries
            if str(item.get("State", "")).lower() == "running"
        }
        db_entries = [item for item in entries if item.get("Service") == "db"]
        database_healthy = all(
            str(item.get("Health", "")).lower() in {"", "healthy"}
            for item in db_entries
        )
        expected = {"db", "odoo"}
        running = expected.issubset(running_services) and database_healthy
        summary = (
            "Docker runtime is running"
            if running
            else f"Docker runtime incomplete; services={','.join(services) or 'none'}"
        )
        return RuntimeInspection(bool(entries), running, services, summary)

    def destroy(self, build_id: str, workspace_path: Path) -> None:
        workspace = self._validated_workspace(build_id, workspace_path)
        compose_path = workspace / "runtime" / "compose.yaml"
        if compose_path.exists():
            result = subprocess.run(
                [
                    "docker",
                    "compose",
                    "--project-name",
                    build_id.replace("-", "_"),
                    "--file",
                    str(compose_path),
                    "down",
                    "--volumes",
                    "--remove-orphans",
                ],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=self.settings.command_timeout_seconds,
                check=False,
            )
            log_path = workspace / "logs" / "destroy.log"
            log_path.write_text(f"{result.stdout}{result.stderr}"[-1_000_000:], encoding="utf-8")
            if result.returncode != 0:
                raise RuntimeOperationError(f"Compose destruction failed; see {log_path}")

    def _run(self, build: Build, stage: str, arguments: list[str]) -> CommandResult:
        compose_path = self._compose_path(build)
        command = [
            "docker",
            "compose",
            "--project-name",
            build.compose_project_name,
            "--file",
            str(compose_path),
            *arguments,
        ]
        started = time.monotonic()
        try:
            result = subprocess.run(
                command,
                cwd=build.workspace_path,
                capture_output=True,
                text=True,
                timeout=self.settings.command_timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeOperationError(f"{stage} command could not complete: {exc}") from exc
        log_path = build.workspace_path / "logs" / f"{stage}.log"
        log_path.write_text(f"{result.stdout}{result.stderr}"[-1_000_000:], encoding="utf-8")
        if result.returncode != 0:
            raise RuntimeOperationError(f"{stage} failed with exit code {result.returncode}")
        return CommandResult(
            exit_code=result.returncode,
            duration_seconds=time.monotonic() - started,
            log_path=str(log_path),
            summary=f"{stage} completed",
        )

    def _compose_path(self, build: Build) -> Path:
        self._validated_workspace(build.id, build.workspace_path)
        return build.workspace_path / "runtime" / "compose.yaml"

    @staticmethod
    def _addons_path(build: Build) -> str:
        repositories = sorted(
            build.repositories, key=lambda item: (item.addons_priority, item.name)
        )
        return ",".join(
            ["/usr/lib/python3/dist-packages/odoo/addons"]
            + [f"/mnt/addons/{item.name}" for item in repositories]
        )

    def _validated_workspace(self, build_id: str, workspace_path: Path) -> Path:
        root = self.settings.builds_root.resolve()
        actual = workspace_path.resolve()
        if actual != (root / build_id).resolve() or actual.parent != root:
            raise RuntimeOperationError(f"Workspace is outside configured root: {actual}")
        return actual

    @staticmethod
    def _result(started: float, log_path: Path, summary: str) -> CommandResult:
        return CommandResult(
            exit_code=0,
            duration_seconds=time.monotonic() - started,
            log_path=str(log_path),
            summary=summary,
        )

    @staticmethod
    def _parse_compose_ps(output: str) -> list[dict[str, object]]:
        content = output.strip()
        if not content:
            return []
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return [item for item in parsed if isinstance(item, dict)]
            if isinstance(parsed, dict):
                return [parsed]
        except json.JSONDecodeError:
            entries: list[dict[str, object]] = []
            for line in content.splitlines():
                try:
                    item = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise RuntimeOperationError(
                        "Docker runtime inspection returned invalid JSON"
                    ) from exc
                if isinstance(item, dict):
                    entries.append(item)
            return entries
        raise RuntimeOperationError("Docker runtime inspection returned invalid JSON")
