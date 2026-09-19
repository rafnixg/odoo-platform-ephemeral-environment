# Mini-Runbot for Odoo 16 (PoC)

This repository currently contains **Phase 0**: a tested domain model and a local vertical
slice that creates, persists, reads, lists, and idempotently destroys build records. It does
not clone repositories or start Odoo yet.

## What works

- Explicit and validated build state transitions.
- SQLite persistence shared by the CLI and FastAPI application.
- Restrictive validation of repository aliases, Git refs, module names, and build IDs.
- Per-build workspace reservation below a configured build root.
- Idempotent destruction through a replaceable runtime port.
- CLI and HTTP endpoints for the Phase 0 lifecycle.
- A read-only `doctor` command for Python, Git, Docker, Compose, paths, and Docker daemon.

## Setup

Python 3.12 is the target version. From the repository root:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

If Python 3.12 is not installed, Python 3.13 can run the current slice, but this does not
replace validation on the target version.

## CLI

```powershell
mini-runbot build create --repo custom --ref feature/x --modules module_a,module_b
mini-runbot build list
mini-runbot build get BUILD_ID
mini-runbot build destroy BUILD_ID
mini-runbot doctor
```

By default, state is stored in `./mini_runbot.db` and workspaces in `./builds`. Override these
with `MINI_RUNBOT_DATABASE_URL` and `MINI_RUNBOT_BUILDS_ROOT`.

## API

```powershell
uvicorn mini_runbot.api.app:app --reload
```

Available operations are `POST /builds`, `GET /builds`, `GET /builds/{build_id}`, and
`DELETE /builds/{build_id}`. In Phase 0, `POST /builds` only creates the build record and
reserves its local workspace; execution is deliberately not started.

Example:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/builds `
  -ContentType application/json `
  -Body '{"repository":"custom","ref":"feature/x","modules":["module_a"]}'
```

## Tests and checks

```powershell
python -m pytest
ruff check .
```

See [ADR 0001](docs/decisions/0001-phase-0-architecture.md) for architecture, assumptions,
the checkout/Compose strategy, and the information still required for the real Odoo slice.

