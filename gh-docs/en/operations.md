# Operations and security

## Local state

Treat the following as operator-owned:

- `config.local.yaml` and other private configuration.
- `mini_runbot.db` and other SQLite databases.
- Workspaces and logs under `builds/`.
- Containers, networks, and volumes belonging to existing builds.

Do not remove or recreate an existing build during verification. Create an identifiable build and
clean up only its resources afterward.

## Failures and evidence

A failed stage preserves its name, exit code, message, and log. If later cleanup also fails, the
original error remains the primary cause. With `retain_failed_runtime: true`, failed resources stay
available for manual inspection.

Destruction uses the build's validated Compose project and workspace, runs `down --volumes
--remove-orphans`, and is safe to retry. Audit data and logs are retained by default.

## Expiry and retention

- `cleanup_interval_seconds > 0` enables the scheduler in the API process.
- `cleanup --expired` destroys runtimes past their TTL.
- `destroyed_retention_seconds: 0` retains evidence indefinitely.
- Positive retention plus `cleanup --retained` purges old destroyed rows and workspaces.

## Security model

- Clients can only submit configured aliases, never arbitrary URLs or paths.
- Refs, modules, targets, IDs, and log paths are validated at trust boundaries.
- External commands receive argument arrays and are not invoked through a shell.
- PostgreSQL exposes no host port; previews bind to loopback.
- Credentials and secrets must stay in host facilities, outside configuration and logs.

On Windows, verify that Docker Desktop remains configured for Linux containers. On Linux, protect
`/var/run/docker.sock`: socket access or membership in the `docker` group grants control of the
daemon and must be treated as an administrative privilege.

!!! danger
    An allowed repository can execute Python and processes inside the Odoo runtime. Docker does not
    turn this PoC into a secure multi-tenant service. Use a dedicated host and trusted code.

## Operational limits

There is no authentication, TLS, reverse proxy, durable queue, distributed worker, Kubernetes, or
external secrets manager. SQLite and the local executor target one host.
