# Configuration

Mini-Runbot loads YAML only when `MINI_RUNBOT_CONFIG` points to an existing file. Supported
environment variables take precedence over YAML.

Use `mini-runbot init` to generate this file interactively or `mini-runbot init --defaults` to copy
the bundled example values. Neither variant overwrites an existing destination.

## Example

```yaml
database_url: sqlite:///./mini_runbot.db
builds_root: ./builds
odoo_image: odoo:16.0
postgres_image: postgres:15
port_start: 18000
port_end: 19999
command_timeout_seconds: 900
health_timeout_seconds: 120
max_concurrent_builds: 2
cleanup_interval_seconds: 60
destroyed_retention_seconds: 0
load_demo_data: true
retain_failed_runtime: false
repositories:
  custom:
    url: https://github.com/OCA/e-commerce.git
    default_ref: "16.0"
    target: custom-addons
    addons_subpath: .
    allow_request_ref: true
    addons_priority: 100
```

## General settings

| Setting | Default | Purpose |
| --- | --- | --- |
| `database_url` | `sqlite:///./mini_runbot.db` | Audit database and leases. |
| `builds_root` | `./builds` | Per-build workspaces and logs. |
| `odoo_image` | `odoo:16.0` | Odoo image used when no profile applies. |
| `postgres_image` | `postgres:15` | Internal PostgreSQL image used when no profile applies. |
| `odoo_versions` | empty | Per-build image profiles; see [Odoo versions](#odoo-versions). |
| `port_start`, `port_end` | `18000`, `19999` | Loopback preview range. |
| `command_timeout_seconds` | `900` | External command timeout. |
| `health_timeout_seconds` | `120` | HTTP healthcheck timeout. |
| `max_concurrent_builds` | `2` | API executor workers. |
| `cleanup_interval_seconds` | `0` | Scheduler frequency; zero disables it. |
| `destroyed_retention_seconds` | `0` | Time before purge; zero retains indefinitely. |
| `load_demo_data` | `true` | Loads demo records used by many Odoo/OCA tests. |
| `retain_failed_runtime` | `false` | Keeps failed containers for diagnosis. |

## Odoo versions

`odoo_versions` maps a profile name to the images a build runs on. `postgres_image` is optional
and inherits the global value.

```yaml
odoo_versions:
  "16.0": {odoo_image: odoo:16.0, postgres_image: postgres:15}
  "17.0": {odoo_image: odoo:17.0, postgres_image: postgres:15}
  "18.0": {odoo_image: odoo:18.0, postgres_image: postgres:16}
  "19.0": {odoo_image: odoo:19.0, postgres_image: postgres:16}
  "20.0": {odoo_image: odoo:20.0, postgres_image: postgres:16}
```

A build resolves its profile in this order:

1. The requested profile: `--odoo-version`, the dashboard selector, or `odoo_version` in the API.
   An unknown name is rejected.
2. The Git reference of the first repository, when it equals a profile name or starts with one
   followed by `-`, `_`, or `/` (`17.0`, `17.0-fix-payment`). The longest name wins.
3. The global `odoo_image` and `postgres_image`, reported as `default`.

The resolved images are stored with the build, so later configuration changes do not alter
existing builds. Profile names use letters, digits, `.`, `_`, and `-`; `default` is reserved.

The runtime adapts to the series of the image: demo data is requested explicitly from 19.0, where
it is no longer loaded by default, and the preview server always listens on every container
interface, which 20.0 no longer does on its own. The `install` stage fails when Odoo leaves a
requested module uninstalled, for example because its manifest version targets another series.

The Compose template mounts the database volume at `/var/lib/postgresql/data`; use PostgreSQL
images that keep their data there (up to `postgres:17`).

## Repositories

Each key under `repositories` is a trusted alias. `target` must be unique, `addons_subpath` must be
relative and remain inside the checkout, and `allow_request_ref: false` restricts requests to
`default_ref`. A lower `addons_priority` number has higher precedence.

Remote HTTPS/SSH credentials must come from a Git credential helper available on the host (for
example, Git Credential Manager on Windows) or from SSH. Never embed them in a URL or commit them.

Use `/` as the YAML path separator where possible: it works on Windows and Linux. Local repository
paths still belong to the host, so a `config.local.yaml` might use `C:/repos/addons` on Windows or
`/srv/repos/addons` on Linux. Do not share one absolute-path configuration between operating
systems.

## Environment variables

| Variable | Overrides |
| --- | --- |
| `MINI_RUNBOT_CONFIG` | YAML file path. |
| `MINI_RUNBOT_DATABASE_URL` | `database_url`. |
| `MINI_RUNBOT_BUILDS_ROOT` | `builds_root`. |
| `MINI_RUNBOT_ODOO_IMAGE` | `odoo_image` (the global image only, not `odoo_versions`). |
| `MINI_RUNBOT_CLEANUP_INTERVAL_SECONDS` | `cleanup_interval_seconds`. |

`config.local.yaml`, SQLite databases, and `builds/` are operator-owned local state and must not be
committed. On both systems, the process user needs read access to repositories and write access to
the SQLite database and `builds_root`.
