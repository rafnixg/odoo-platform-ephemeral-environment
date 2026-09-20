# Mini-Runbot for Odoo 16 (PoC)

Mini-Runbot turns an allowed Git revision and a list of Odoo modules into an isolated,
tested, temporary Odoo 16 instance. It is a single-host proof of concept, not a hardened
service for untrusted code.

## What works

- Fetches configured local or HTTPS/SSH Git repositories, resolves requested refs to immutable
  SHAs, and creates detached isolated checkouts.
- Generates and validates an isolated Docker Compose project per build.
- Runs database, installation, tests, server startup, and HTTP healthcheck as separate stages.
- Persists state, revisions, timings, results, failures, and log paths in SQLite.
- Exposes the same application lifecycle through Typer CLI and FastAPI.
- Executes API builds using a bounded local executor and preserves diagnostic evidence.
- Supports TTL cleanup, restart recovery, safe log reads, and idempotent destruction.
- Includes a controlled Odoo module fixture for an end-to-end demonstration.

## Setup

Python 3.12 is the target version. From the repository root:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Docker Desktop with Linux containers must be running. Copy `config.example.yaml`, configure
only authorized Git repositories, then set `MINI_RUNBOT_CONFIG` to its absolute path.
Python 3.13 can run the code, but Python 3.12 remains the target version.

Repository inputs are aliases from configuration, never arbitrary API paths or URLs. Each entry
can point to a local Git repository or an HTTPS/SSH remote and can set `addons_subpath` when its
Odoo modules are below the repository root. Remote checkouts use a shallow fetch of only the
requested ref; credentials must come from Git Credential Manager or SSH, never from the URL.

## CLI

```powershell
mini-runbot build create --repo custom --ref feature/x --modules module_a,module_b --run
mini-runbot build list
mini-runbot build list --status running
mini-runbot build get BUILD_ID
mini-runbot build logs BUILD_ID --stage test
mini-runbot build destroy BUILD_ID
mini-runbot cleanup --expired
mini-runbot recover
mini-runbot doctor
```

CLI output uses readable tables and pipeline panels by default. Add `--json` to create, get,
list, run, destroy, cleanup, or recover when another program consumes the output.

By default, state is stored in `./mini_runbot.db` and workspaces in `./builds`. Override these
with `MINI_RUNBOT_DATABASE_URL` and `MINI_RUNBOT_BUILDS_ROOT`.

## API

```powershell
mini-runbot serve --reload
```

Open `http://127.0.0.1:8000` for the built-in dashboard. It provides build metrics, filtering,
creation, live polling, stage timelines, safe log viewing, preview links, and runtime destruction.
The frontend is served by FastAPI and needs no separate Node.js build or deployment.
Runtime destruction is rejected while the in-process worker is still executing the build, avoiding
concurrent lifecycle transitions and partial resource cleanup.

Available operations are `POST /builds`, `GET /builds`, `GET /builds/{build_id}`,
`GET /builds/{build_id}/logs?stage=test`, and `DELETE /builds/{build_id}`. `POST /builds`
returns `202` after persistence and dispatches execution to a bounded in-process executor.
The executor is intentionally not a durable queue; interrupted builds can be classified with
`BuildManager.recover_interrupted()` during controlled startup recovery.

Example:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/builds `
  -ContentType application/json `
  -Body '{"repository":"custom","ref":"feature/x","modules":["module_a"]}'
```

## Controlled demo

The repository contains `demo_addons/mini_runbot_demo`. After committing the current source
and starting Docker Desktop, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\demo.ps1
```

The demo resolves this repository's `HEAD`, records the SHA, mounts only `demo_addons`, starts
PostgreSQL 15 and Odoo 16, installs and tests the fixture, then leaves Odoo available on an
allocated loopback port. Destroy the reported build when finished.

## Pipeline and isolation

```text
NEW -> CHECKING_OUT -> PREPARING -> INSTALLING -> TESTING -> STARTING -> RUNNING
                                  \ failure at any validation stage -> FAILED
RUNNING -> EXPIRED -> DESTROYING -> DESTROYED
```

Every build has its own workspace, Compose project, network, PostgreSQL volume/database, and
loopback host port. PostgreSQL is not exposed on the host. Containers have memory, CPU, PID,
and log-size limits. Docker isolation is not a security boundary for hostile repositories;
run the orchestrator only on a dedicated host with trusted code.

Build evidence is retained under `builds/BUILD_ID/logs`. Destruction removes Compose runtime
resources but keeps the audit row and logs. API log output is restricted and truncated.

## Tests and checks

```powershell
python -m pytest
python -m ruff check .
```

Tests marked `docker` can be excluded with `python -m pytest -m "not docker"`. Unit and local
integration tests do not require Docker.

## Current limitations

- The local executor and port reservations are process-local, not distributed or durable.
- SQLite is intended for one orchestrator process.
- No webhook, GitHub Checks, reverse proxy, TLS, Kubernetes, or external secrets manager.
- The bundled Compose template uses local PoC database credentials and trusted repositories.
- A real Docker/Odoo run still requires the host daemon and image registry to be available.

Architecture decisions are recorded in [ADR 0001](docs/decisions/0001-phase-0-architecture.md)
and [ADR 0002](docs/decisions/0002-local-execution-and-recovery.md).
