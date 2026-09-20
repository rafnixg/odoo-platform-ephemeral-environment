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
- [ ] Structured log streaming and build cancellation.

## Phase 4: external integration — optional

- GitHub webhooks and Checks status reporting.
- Durable queue and separate workers.
- Authentication, authorization, TLS, and secrets integration.
- Reverse proxy and stable preview routes.

Kubernetes and multi-host scheduling remain out of scope until the single-host flow demonstrates
enough operational value.
