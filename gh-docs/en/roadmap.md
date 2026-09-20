# Mini-Runbot roadmap

This roadmap keeps the proof of concept focused on validating the Odoo lifecycle before introducing
distributed infrastructure.

## Phase 0: lifecycle foundation — complete

- Domain state machine, SQLite audit trail, CLI, and API.
- Safe workspaces, lifecycle cleanup, logs, and recovery classification.

## Phase 1: real isolated execution — complete

- Configured local and HTTPS/SSH Git sources resolved to immutable SHAs.
- Per-build Docker Compose, PostgreSQL, Odoo install/test stages, and HTTP healthcheck.
- Dashboard, bounded local executor, TTL cleanup, and controlled E2E fixture.

## Phase 2: composed addon builds — complete

- Up to ten configured repositories with independent refs.
- Persisted alias, ref, SHA, checkout, and addon priority.
- Deterministic `addons_path` and one contract across CLI, API, and dashboard.
- Duplicate alias and checkout target rejection before resource creation.

## Phase 3: host reliability — in progress

- [x] Transactional SQLite port leases across processes.
- [x] Explicit orphaned and missing lease reconciliation during recovery.
- [x] Configurable scheduled cleanup in the API process.
- [x] Opt-in audit and log retention/deletion policy.
- [x] Recovery reconciliation between registered builds and real Docker services.
- [x] Bilingual documentation and automated quality and security checks.

### Execution control and logs — next increment

- [ ] Introduce versioned SQLite migrations before adding states and events.
- [ ] Extract a portable `CommandRunner` that manages processes and process groups on Windows and
  Linux.
- [ ] Add `CANCEL_REQUESTED`, `CANCELLING`, and `CANCELLED` states with idempotent cleanup while
  preserving the original reason.
- [ ] Expose cancellation through the API, CLI, and dashboard for queued and running builds.
- [ ] Capture `stdout` and `stderr` incrementally as structured events per build and stage.
- [ ] Publish events through Server-Sent Events with a reconnection cursor while retaining
  historical log queries.
- [ ] Cover cancellation, timeouts, and race conditions during checkout, installation, tests,
  healthcheck, and queueing.

### Additional host hardening

- [ ] Run non-Docker tests in a Windows and Linux CI matrix.
- [ ] Run the real Docker/Odoo E2E through a manual and scheduled workflow on Linux.
- [ ] Add pagination, sorting, and status, repository, and date filters to the builds API.
- [ ] Add liveness and readiness endpoints for configuration, SQLite, Docker, and the executor.
- [ ] Apply configurable CPU, memory, process, and available-disk limits per build.
- [ ] Allow retrying a build with the same SHAs or creating a new one from current refs without
  conflating the two behaviors.
- [ ] Export a diagnostic bundle containing logs, stages, revisions, and rendered Compose.
- [ ] Expose optional queue, build, stage-duration, failure, and cleanup metrics.
- [ ] Document service operation on Windows and Linux, backup and restore, troubleshooting, and the
  verified compatibility matrix.
- [x] Pin the Mermaid version and add sequence diagrams for operational flows.

Phase 3 is complete when an operator can safely observe and cancel a real build, recover the
service, and diagnose failures on both supported operating systems.

## Phase 4: external integration — optional

- GitHub webhooks and Checks status reporting.
- Durable queue and separate workers.
- Authentication, authorization, TLS, and secrets integration.
- Reverse proxy and stable preview routes.

Kubernetes and multi-host scheduling remain out of scope until the single-host flow demonstrates
enough operational value.
