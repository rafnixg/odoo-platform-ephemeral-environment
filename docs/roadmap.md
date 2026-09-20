# Mini-Runbot roadmap

This roadmap keeps the proof of concept focused on validating the Odoo build lifecycle before
introducing distributed infrastructure.

## Phase 0: lifecycle foundation — complete

- Domain state machine, SQLite audit trail, CLI, and API.
- Safe workspaces, lifecycle cleanup, logs, and recovery classification.

## Phase 1: real isolated execution — complete

- Configured local and HTTPS/SSH Git sources resolved to immutable SHAs.
- Per-build Docker Compose, PostgreSQL, Odoo install/test/start stages, and HTTP healthcheck.
- Dashboard, bounded local executor, TTL cleanup, and controlled end-to-end fixture.

## Phase 2: composed addon builds — complete

- Select up to ten configured repositories with independent Git refs.
- Preserve each repository's origin alias, ref, SHA, checkout, and addons priority.
- Build a deterministic `addons_path` and expose the same contract in CLI, API, and dashboard.
- Reject duplicate aliases and checkout targets before resource creation.

## Phase 3: host reliability — in progress

- [x] Transactional SQLite port leases across orchestrator processes.
- [x] Explicit reconciliation of orphaned and missing leases during recovery.
- [x] Configurable scheduled expiry cleanup in the API process.
- [ ] Explicit audit and log retention/deletion policy.
- [ ] Stronger startup reconciliation against actual Docker resources.
- [ ] Structured log streaming and build cancellation.

## Phase 4: external integration — optional after PoC validation

- GitHub webhooks and Checks status reporting.
- Durable queue and separate workers.
- Authentication, authorization, TLS, and secrets integration.
- Reverse proxy and stable preview routing.

Kubernetes and multi-host scheduling are intentionally out of scope until the single-host flow
has demonstrated enough value to justify the operational complexity.
