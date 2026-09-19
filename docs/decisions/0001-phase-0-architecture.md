# ADR 0001: Phase 0 architecture and execution strategy

- Status: Accepted for Phase 0
- Date: 2026-09-19

## Context

The repository was empty apart from `.git`. The inspected host has Python 3.13.2, Git 2.55,
Docker 28.5.1, and Compose 2.40, but Docker Desktop's Linux daemon was not running. No Odoo,
Enterprise, or custom-addons repositories, image, modules, or dependency manifests were
available.

## Decision

The first increment uses a framework-independent domain model, narrow repository and runtime
ports, SQLite through SQLAlchemy, and shared application services for Typer and FastAPI.
`POST /builds` creates a build synchronously but does not execute it. A local runtime adapter
only reserves a controlled workspace and removes its empty runtime marker during destruction;
logs and the audit row are retained.

The state machine is explicit. Normal execution follows:

```text
NEW -> CHECKING_OUT -> PREPARING -> INSTALLING -> TESTING -> STARTING -> RUNNING
```

Any active state may fail. Any non-destroyed state may enter `DESTROYING`, followed by
`DESTROYED`; destroying an already destroyed build is a successful no-op. `RUNNING` may become
`EXPIRED`, and an expired build can be destroyed.

## Phase 1 checkout strategy

Only configured repository aliases will be accepted. For each build, Git will resolve the
requested ref to a commit SHA before checkout. It will then create an isolated clone/worktree
inside `<builds_root>/<validated_build_id>/sources/<configured_target>`. User working trees will
never be checked out or modified. Subprocess calls will use argument arrays without a shell,
and both repository aliases and target paths will be validated against configuration.

The exact origin, requested ref, resolved SHA, checkout target, and addons priority will be
persisted. Remote origins will require an explicit allowlist; credentials will come from the
host's existing Git configuration and never from API payloads.

## Phase 1 Docker Compose strategy

A Jinja template will render into the build workspace using only validated/generated values.
Each build gets a Compose project name, internal network, PostgreSQL volume, database name,
workspace, and host port derived from its immutable ID or allocated transactionally. PostgreSQL
will not publish a host port. The generated file must pass `docker compose config` before any
resource is created. Compose commands will use argument arrays, a fixed working directory, a
timeout, and the explicit project name. Destruction will run `down --volumes --remove-orphans`
only for that validated project and workspace and will be safe to retry.

Install, test, and server startup will be separate Compose invocations. A build reaches
`RUNNING` only after both commands succeed and the HTTP healthcheck passes.

## Unknowns required before real Odoo execution

The following are intentionally not invented and block Phase 1's real Odoo validation:

- Authorized local paths or URLs for Odoo Community, Enterprise (if used), and custom addons.
- Authorized Git authentication method and repository allowlist.
- Approved Odoo 16 image or project Dockerfile.
- Initial demonstration modules and their Python/system dependencies.
- Correct `addons_path` ordering and whether Enterprise is required.
- Host network/proxy/registry restrictions and usable preview port range.
- Desired TTL and log/evidence retention policy.

These inputs are not needed to verify Phase 0.

## Consequences

The domain and application code can be tested without Docker and can later accept Git and
Compose adapters without changing CLI/API lifecycle rules. Phase 0 does not prove real Git,
PostgreSQL, or Odoo execution; that claim remains explicitly pending.

