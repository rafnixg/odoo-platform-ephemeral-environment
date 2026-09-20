# Glossary

| Term | Definition |
| --- | --- |
| Addons path | Ordered locations where Odoo discovers modules. A lower priority is evaluated first. |
| Allowlist alias | Operator-configured name representing a trusted Git source. |
| Build | Isolated execution of revisions and modules with its own lifecycle, workspace, and resources. |
| Composed build | Build made from several repositories with independent refs. |
| Detached checkout | Working tree pinned to a commit without remaining attached to a mutable branch. |
| Cleanup | Destruction of expired build resources; it does not necessarily purge audit data. |
| Compose project | Isolated name used by Docker Compose for the build's services, network, and volumes. |
| Terminal state | State with no normal forward progression; `DESTROYED` allows idempotent repetition. |
| Stage | Auditable pipeline operation with status, timing, output, log, and summary. |
| Filestore | Odoo attachment storage isolated in one volume per Compose project. |
| Healthcheck | Final verification that the Odoo preview responds over HTTP. |
| Port lease | Persistent reservation assigning one loopback port exclusively to a build. |
| Optimistic locking | Concurrency control rejecting a write when `Build.version` has changed. |
| Git source | HTTPS/SSH URL or local path configured for an alias. |
| Preview | Temporary Odoo instance published on `127.0.0.1:<port>`. |
| Purge | Later removal of the record and workspace for an already destroyed build. |
| Recovery | Explicit reconciliation of SQLite, Docker, and leases after a restart. |
| Requested ref | Branch, tag, or SHA requested by the user and resolved before execution. |
| Revision | Stored alias, source, ref, SHA, checkout, and priority combination. |
| Immutable SHA | Exact commit identifying the code that was actually tested. |
| TTL | Time from build creation until it becomes eligible for expiration. |
| Workspace | `<builds_root>/<build_id>` containing sources, runtime configuration, and logs. |

## Stage names

`checkout` → `render` → `compose_validate` → `database` → `install` → `test` → `start` →
`healthcheck`.

See the [domain model](domain-model.md) for states and validation and the
[pipeline](build-pipeline.md) for each stage's behavior.
