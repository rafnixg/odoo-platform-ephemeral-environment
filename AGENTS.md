# AGENTS.md

This file defines the working conventions for automated coding agents in this repository.
It applies to the entire repository unless a more specific `AGENTS.md` exists in a subdirectory.

## Project purpose

Mini-Runbot is a local, single-host proof of concept for turning configured Git revisions and
Odoo module lists into isolated, tested, temporary Odoo 16 environments. It is intended for
trusted repositories and is not a security boundary for hostile code.

Keep changes aligned with the current roadmap in `gh-docs/es/roadmap.md`. Do not introduce
distributed infrastructure, Kubernetes, or unrelated platform features unless the task explicitly
requires it.

## Supported environment

- Python 3.12 is the target version.
- On Windows, Docker Desktop must use Linux containers and PowerShell must be supported.
- On Linux, Docker Engine with the Compose v2 plugin and Bash must be supported.
- Keep application behavior and documentation portable across Windows and Linux; avoid
  shell-specific assumptions in shared code.
- Git repository inputs must come from configured aliases. Do not accept arbitrary repository URLs
  or filesystem paths from API or CLI requests.

Install the development environment from the repository root:

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Linux Bash:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Architecture

- `src/mini_runbot/domain`: domain models, states, and errors. Keep this layer independent of
  infrastructure details.
- `src/mini_runbot/application`: build orchestration and lifecycle use cases.
- `src/mini_runbot/adapters`: Git, persistence, and Docker Compose implementations.
- `src/mini_runbot/api` and `src/mini_runbot/cli`: transport layers over the same application
  behavior.
- `src/mini_runbot/web`: dashboard assets served directly by FastAPI.
- `src/mini_runbot/templates`: packaged Docker Compose runtime definitions.
- `tests/unit`: fast isolated tests.
- `tests/integration`: local integration tests that normally do not require Docker.
- `tests/e2e`: real lifecycle coverage; tests marked `docker` require a working daemon.
- `demo_addons`: controlled Odoo fixture used by the end-to-end demonstration.

Preserve dependency direction: transports and adapters may depend on application/domain contracts;
the domain must not depend on FastAPI, Typer, SQLAlchemy, Git, or Docker Compose.

## Development rules

- Use `pathlib.Path` for filesystem paths and account for Windows path behavior.
- Keep CLI and API lifecycle semantics consistent when adding or changing an operation.
- Preserve immutable commit SHA resolution, detached checkouts, deterministic addons priority, and
  per-build isolation.
- Validate repository aliases, refs, module names, checkout targets, build IDs, and log paths at
  their trust boundaries.
- Keep build transitions explicit and persist useful failure evidence, including the failed stage,
  exit code, message, and log path.
- Runtime cleanup must be idempotent. A cleanup failure must not hide the original build failure.
- Keep PostgreSQL and Odoo filestore volumes isolated per Compose project.
- Load Odoo demo data by default because Odoo/OCA tests can depend on demo XML records. Respect the
  `load_demo_data` setting for production-like previews.
- Update `README.md`, `config.example.yaml`, ADRs, or the roadmap when a change affects documented
  behavior or configuration.
- Do not add credentials, tokens, SSH keys, or repository secrets to source, logs, fixtures, or
  examples.

## Local state and safety

Treat the following as user-owned local state:

- `config.local.yaml`
- `mini_runbot.db` and other local SQLite databases
- `builds/` workspaces and logs
- Docker containers, networks, and volumes belonging to existing builds

Never commit local configuration or generated runtime state. Do not destroy, expire, recreate, or
otherwise mutate an existing build unless the user explicitly requests it. For verification, create
a uniquely identifiable build and clean up only that build when the check is complete. If a
successful preview is intentionally left running for the user, report its build ID and URL.

Do not rewrite or discard unrelated working-tree changes. Stage only files that belong to the
current task.

## Verification

Run the smallest relevant tests while iterating, then use the full local checks before handing off a
substantial change:

```powershell
python -m pytest
python -m ruff check .
git diff --check
```

Frontend JavaScript changes should also pass:

```powershell
node --check src\mini_runbot\web\app.js
```

Tests that do not need Docker can be selected with:

```powershell
python -m pytest -m "not docker"
```

Run a real Docker/Odoo build when changing checkout, Compose rendering, installation, testing,
startup, health checks, ports, volumes, or cleanup. Use a configured repository alias and inspect
both the persisted stage results and their log files. A real run is not successful merely because
the containers started: confirm the requested modules installed, Odoo tests reported no failures,
and the preview returned HTTP 200.

## Git conventions

- Keep commits focused and use imperative Conventional Commit subjects such as `feat:`, `fix:`,
  `test:`, `docs:`, or `refactor:`.
- Do not amend, rebase, force-push, or push unless the user explicitly requests it.
- Before committing, review `git status --short` and ensure local configuration, databases,
  workspaces, and unrelated user changes are excluded.

## Completion report

Summarize the behavior changed, verification performed, and any runtime intentionally left active.
Mention skipped Docker validation, cleanup limitations, or remaining roadmap work explicitly rather
than implying it was completed.
