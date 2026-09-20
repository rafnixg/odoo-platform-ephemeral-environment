# ADR 0002: local execution, persistence, and recovery

- Status: accepted for the PoC
- Date: 2026-09-19

## Decision

The API dispatches builds to a bounded local thread pool. This lets `POST /builds` return quickly
without Redis or an external queue. CLI execution with `--run` is synchronous. Both paths call the
same `BuildManager` pipeline.

Every completed stage is persisted immediately. After a confirmed restart, `recover_interrupted`
marks interrupted execution with a diagnostic, reconciles resources, and retries builds in
`DESTROYING`. Recovery is explicit so it cannot interfere with another live API process.

Logs live below the validated build workspace. The API only reads recorded paths whose direct
parent is the build's `logs` directory and limits the response to 100 KB.

Preview ports are coordinated between local processes through transactional SQLite leases. Recovery
removes orphaned leases and restores missing leases when a runtime remains active.

## Limitations

The executor is not durable: in-memory tasks are lost when the process exits. SQLite and the local
pool fit this single-host PoC, not distributed builders. A durable queue is deferred until its
operational complexity is justified.
