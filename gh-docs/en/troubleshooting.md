# Troubleshooting and runbook

Always begin with the built-in diagnostics from the same virtual environment and configuration the
service will use:

```console
mini-runbot doctor
```

`doctor` checks Python, Git, the Docker CLI, Compose v2, the daemon, `builds_root`, and repositories.
It is a CLI command; there is currently no equivalent HTTP endpoint.

## Diagnostic matrix

| Symptom | Check | Action |
| --- | --- | --- |
| Configuration does not load | Check `MINI_RUNBOT_CONFIG` and that it is an existing absolute path. | Export it again in the process that starts Mini-Runbot. |
| `docker-daemon` fails | Run `docker version` and `docker info`. | Start Docker Desktop or Docker Engine and confirm Linux containers. |
| `compose` fails | Run `docker compose version`. | Install/enable Compose v2; `docker-compose` v1 is insufficient. |
| Remote repository is unavailable | Run `git ls-remote SOURCE REF` as the same user. | Fix the Git/SSH helper; never embed secrets in the URL. |
| `No preview ports are available` | Inspect the range and loopback listeners. | Expand the range or destroy only known builds that are no longer needed. |
| `checkout` fails | Read `checkout.log` and the stored ref. | Confirm alias, ref permission, and the existence of `addons_subpath`. |
| `compose_validate` fails | Read its log and `runtime/compose.yaml`. | Fix images, mounts, or configured values; do not edit an active workspace. |
| `install` fails | Read the latest Odoo output. | Check dependencies, manifest, addon order, and demo data. |
| `test` fails | Read the stage log, not only container state. | Fix the reported Odoo/OCA tests before considering the build valid. |
| `healthcheck` fails | Inspect `start` and `healthcheck.log`. | Check the port, Odoo process, configured timeout, and service logs. |
| State is inconsistent after restart | Stop the old API and run `mini-runbot recover`. | Inspect recovered/failed IDs and their logs before cleanup. |

## Inspecting evidence

```console
mini-runbot build get BUILD_ID
mini-runbot build logs BUILD_ID
mini-runbot build logs BUILD_ID --stage test
```

The API limits log responses to the last 100,000 bytes and verifies that every stored path is a
direct child of `workspace/logs`. To inspect failed containers, enable
`retain_failed_runtime: true` beforehand, then explicitly destroy the build when finished.

## Cleanup and recovery

```console
mini-runbot cleanup --expired
mini-runbot cleanup --retained
mini-runbot recover
```

- `--expired` destroys expired runtimes.
- `--retained` only purges when configured retention is positive.
- `recover` classifies interrupted execution and reconciles Docker and ports.

Do not run recovery while another instance may still be working. Destruction removes the build's
containers and volumes; always confirm the ID.

## Platform-specific notes

=== "Windows · PowerShell"

    - Docker Desktop must use Linux containers.
    - Ensure the drive containing `builds_root` is shared with Docker Desktop.
    - Export configuration in the same console that runs `serve`.

    ```powershell
    $env:MINI_RUNBOT_CONFIG = (Resolve-Path config.local.yaml).Path
    mini-runbot doctor
    ```

=== "Linux · Bash"

    - The user needs Docker socket access and write permission on `builds_root`.
    - Membership in the `docker` group is equivalent to administrative host privileges.
    - Do not solve permission errors by indiscriminately running the whole service as root.

    ```bash
    export MINI_RUNBOT_CONFIG="$(realpath config.local.yaml)"
    mini-runbot doctor
    ```

## Backup and restore

Stop the API, scheduler, and builds before copying state. Back up together:

- the SQLite file referenced by `database_url`;
- `builds_root`, including logs and rendered Compose files;
- private configuration through a secure channel, separate from the repository.

Restore to the same paths or update configuration before running `mini-runbot recover`. A SQLite
backup without its workspaces preserves audit data but cannot provide logs or reconcile every
runtime.

## Escalation

When reporting a problem, include the Mini-Runbot version, operating system, `doctor` output, build
ID, status, failed stage, and log summary. Remove tokens, credential-bearing URLs, and private data.
