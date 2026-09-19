# ADR 0002: Local execution, persistence, and recovery

- Status: Accepted for the PoC
- Date: 2026-09-19

## Decision

The API dispatches builds to a bounded in-process thread pool. This keeps `POST /builds` fast
without introducing Redis or an external queue. CLI execution is synchronous when `--run` is
used. Both paths call the same `BuildManager` pipeline.

Every completed stage is persisted immediately. If the process restarts, `recover_interrupted`
marks builds in execution states as failed with a recovery diagnostic and retries builds already
in `DESTROYING`. Recovery is explicit so a second CLI process cannot incorrectly fail work owned
by a live API process.

Logs are files below the validated build workspace; API reads are restricted to recorded paths
whose direct parent is the build's `logs` directory and are truncated to 100 KB.

## Limitations

The executor is not durable: queued tasks are lost when the process exits. Port reservations are
process-local until Docker binds the selected port. SQLite and a single orchestrator process are
appropriate for this PoC, not for distributed builders. A durable queue and transactional resource
leases are later evolutions if the core Odoo flow proves valuable.
